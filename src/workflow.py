"""工作流编排：LangGraph 把「解析→抽取→判定→修订建议→人工确认→报告」编成状态图。

两条入口共用同一张图：
- **快速模式**（`/api/review`）：`auto_confirm=True`，无高风险直接跑完出报告；
- **人工确认模式**（`/api/review_graph`）：有高风险时在 `confirm` 节点 `interrupt` 暂停，
  人确认后用 `Command(resume=...)` 从断点继续（checkpoint 保证不重跑前面的 LLM 步骤）。

核心逻辑（parser/extract/assess/revision/report）完全复用，LangGraph 只做编排。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

import config
from src.parser import parse, clause_headings
from src import extract as EX
from src import revision
from src import report_agent
from src.assess import assess, _find_clause_text
from src.report import generate_markdown


class ReviewState(TypedDict, total=False):
    filename: str
    path: str  # 上传文件时的临时绝对路径；为空则用 RAW_DIR/filename
    focus: str
    perspective: str
    auto_confirm: bool
    started_at: float
    paragraphs: list
    clauses: list
    judgments: list
    basis_attached: int
    human_review: dict
    report: str
    usage: dict
    process: dict


# ---- 惰性单例：client / 条款类型 ----
_client = None
_types = None


def _get_client():
    global _client
    if _client is None:
        _client = EX.make_client()
    return _client


def _get_types():
    global _types
    if _types is None:
        _types = EX.load_clause_types()
    return _types


# ---- 节点 ----
def parse_node(state: ReviewState) -> dict:
    """解析合同：优先用上传文件的临时路径，否则按示例文件名找。"""
    raw = state.get("path")
    path = Path(raw) if raw else (config.RAW_DIR / state["filename"])
    paragraphs = parse(path)
    return {"paragraphs": paragraphs}


def extract_node(state: ReviewState) -> dict:
    clauses, usage = EX.extract(_get_client(), state["paragraphs"], _get_types())
    clauses = EX.validate(state["paragraphs"], clauses)
    return {"clauses": clauses, "usage": usage}


def assess_node(state: ReviewState) -> dict:
    return {
        "judgments": assess(
            state["clauses"],
            _get_types(),
            state.get("paragraphs"),
            _get_client(),
            state.get("perspective", ""),
        )
    }


def revise_node(state: ReviewState) -> dict:
    """对「偏离 / 冲突」条款生成修订建议（和顺序版逻辑一致）。"""
    judgments = state.get("judgments", []) or []
    paragraphs = state.get("paragraphs", []) or []
    clauses = state.get("clauses", []) or []
    clause_map = {c["type"]: c for c in clauses}
    playbook = {t["name"]: t for t in _get_types()}
    focus = state.get("focus", "")
    perspective = state.get("perspective", "")

    for j in judgments:
        if j.get("present") and j.get("verdict") in ("偏离", "冲突"):
            c = clause_map.get(j["clause"])
            full = (
                _find_clause_text(paragraphs, c.get("clause_no"), c.get("evidence")) if c else ""
            )
            try:
                j["revision"] = revision.generate_revision(
                    j["clause"],
                    full or j.get("evidence", ""),
                    playbook[j["clause"]],
                    _get_client(),
                    focus,
                    perspective,
                )
            except Exception:  # noqa: BLE001
                j["revision"] = ""
    return {"judgments": judgments}


def basis_node(state: ReviewState) -> dict:
    """给判定补「判定依据」（playbook 必备要素 / 红线 / 示范条款 + 可选法条）。纯代码，不调模型。"""
    judgments = state.get("judgments", []) or []
    try:
        attached = report_agent.build_basis(judgments, _get_types())
    except Exception:  # noqa: BLE001
        attached = 0
    return {"judgments": judgments, "basis_attached": attached}


def confirm_node(state: ReviewState) -> dict:
    """高风险条款需人工确认；无高风险或快速模式则直接通过。"""
    high_risk = [j for j in state.get("judgments", []) if j.get("severity") == "高"]
    if state.get("auto_confirm"):
        return {"human_review": {"action": "auto", "high": len(high_risk)}}
    if not high_risk:
        return {"human_review": {"action": "none", "high": 0}}

    # 暂停，把高风险清单交给人，等待决定
    # decision 结构：{"action": "approve" | "edit", "changes": {条款名: {...}}}
    decision = interrupt({
        "action": "human_review",
        "high_risk": high_risk,
        "message": f"发现 {len(high_risk)} 项高风险条款，请确认后生成报告",
    })

    # 应用人的修改（只覆盖传进来的条款）
    if isinstance(decision, dict):
        changes = decision.get("changes") or {}
        if isinstance(changes, dict):
            for j in state.get("judgments", []):
                if j.get("clause") in changes and isinstance(changes[j["clause"]], dict):
                    j.update(changes[j["clause"]])
    return {
        "judgments": state.get("judgments", []),
        "human_review": decision if isinstance(decision, dict) else {"action": "approve"},
    }


def report_node(state: ReviewState) -> dict:
    judgments = state.get("judgments", []) or []
    paragraphs = state.get("paragraphs", []) or []
    usage = state.get("usage") or {}
    started = state.get("started_at") or time.time()

    report = generate_markdown(
        state.get("filename", ""),
        judgments,
        _get_types(),
        usage=usage,
        seconds=round(time.time() - started, 1),
    )
    process = {
        "paragraphs": len(paragraphs),
        "headings": len(clause_headings(paragraphs)),
        "seconds": round(time.time() - started, 1),
        "tokens": usage.get("total_tokens", 0),
    }
    return {"report": report, "process": process}


def build_graph(checkpointer=None):
    """构建并编译工作流图。传入 checkpointer 以支持断点续跑。"""
    g = StateGraph(ReviewState)
    g.add_node("parse", parse_node)
    g.add_node("extract", extract_node)
    g.add_node("assess", assess_node)
    g.add_node("revise", revise_node)
    g.add_node("basis", basis_node)
    g.add_node("confirm", confirm_node)
    g.add_node("report", report_node)

    g.add_edge(START, "parse")
    g.add_edge("parse", "extract")
    g.add_edge("extract", "assess")
    g.add_edge("assess", "revise")
    g.add_edge("revise", "basis")
    g.add_edge("basis", "confirm")
    g.add_edge("confirm", "report")
    g.add_edge("report", END)

    return g.compile(checkpointer=checkpointer)


def new_app():
    """返回一个带内存 checkpointer 的编译图。"""
    return build_graph(checkpointer=MemorySaver())


__all__ = ["ReviewState", "build_graph", "new_app", "Command"]
