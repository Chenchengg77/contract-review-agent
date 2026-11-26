"""工作流编排：用 LangGraph 把「解析→抽取→判定→人工确认→报告」编成状态图。

相比手写顺序脚本，LangGraph 带来两点（对应 Day13）：
1. 显式状态机：每个步骤是独立节点，state 统一传递中间结果；
2. 人工确认（human-in-the-loop）：高风险条款在写报告前用 interrupt 暂停，
   等人 approve/edit 后用 Command(resume=...) 恢复，checkpoint 保证断点可续跑。

注意：核心逻辑（parser/extract/assess/report）完全复用，LangGraph 只做编排。
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

import config
from src.parser import parse
from src import extract as EX
from src.assess import assess
from src.report import generate_markdown


class ReviewState(TypedDict, total=False):
    filename: str
    paragraphs: list
    clauses: list
    judgments: list
    human_review: dict
    report: str
    usage: dict


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
    paragraphs = parse(config.RAW_DIR / state["filename"])
    return {"paragraphs": paragraphs}


def extract_node(state: ReviewState) -> dict:
    clauses, usage = EX.extract(_get_client(), state["paragraphs"], _get_types())
    clauses = EX.validate(state["paragraphs"], clauses)
    return {"clauses": clauses, "usage": usage}


def assess_node(state: ReviewState) -> dict:
    return {"judgments": assess(state["clauses"], _get_types(), state.get("paragraphs"), _get_client())}


def confirm_node(state: ReviewState) -> dict:
    """高风险条款需人工确认；无高风险则直接通过。"""
    high_risk = [j for j in state["judgments"] if j.get("severity") == "高"]
    if not high_risk:
        return {"human_review": {}}

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
            for j in state["judgments"]:
                if j.get("clause") in changes and isinstance(changes[j["clause"]], dict):
                    j.update(changes[j["clause"]])
    return {"judgments": state["judgments"], "human_review": decision if isinstance(decision, dict) else {"action": "approve"}}


def report_node(state: ReviewState) -> dict:
    report = generate_markdown(
        state["filename"], state["judgments"], _get_types(), usage=state.get("usage")
    )
    return {"report": report}


def build_graph(checkpointer=None):
    """构建并编译工作流图。传入 checkpointer 以支持断点续跑。"""
    g = StateGraph(ReviewState)
    g.add_node("parse", parse_node)
    g.add_node("extract", extract_node)
    g.add_node("assess", assess_node)
    g.add_node("confirm", confirm_node)
    g.add_node("report", report_node)

    g.add_edge(START, "parse")
    g.add_edge("parse", "extract")
    g.add_edge("extract", "assess")
    g.add_edge("assess", "confirm")
    g.add_edge("confirm", "report")
    g.add_edge("report", END)

    return g.compile(checkpointer=checkpointer)


def new_app():
    """返回一个带内存 checkpointer 的编译图（单份合同审查用）。"""
    return build_graph(checkpointer=MemorySaver())


__all__ = ["ReviewState", "build_graph", "new_app", "Command"]
