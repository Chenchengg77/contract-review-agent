"""风险判定引擎：把抽取出的条款与 playbook 比对，给出 verdict + severity + reason。

分层判定：
1. 规则层（零成本、可解释）：
   - 条款缺失（present=false）→ 缺失，severity 按 playbook
   - 条款存在但无正文 → 偏离（中）
2. 语义层（LLM，判合规/偏离/冲突）：
   - 条款存在且有正文时，交给 LLM 对照 playbook 的 must_contain / red_flags 判定
   - 传入 paragraphs + client 即启用；不传则退化为纯规则层
"""

from __future__ import annotations

import json

import config
from src.judge import judge_clause

# 缺失时判定为「高」风险的条款类型（与 playbook 的 severity_rule 一致）
_MISSING_SEVERITY = {
    "付款条款": "高", "违约金": "高", "争议解决": "高",
    "保密条款": "高", "知识产权": "高", "责任上限": "高",
}


def load_playbook() -> list[dict]:
    data = json.loads((config.PLAYBOOK_DIR / "clauses.json").read_text(encoding="utf-8"))
    return data["clause_types"]


def _find_clause_text(paragraphs: list[dict], clause_no: str, evidence: str) -> str:
    """从段落里找该条款的完整正文（优先按条款号，退而按 evidence 前缀）。"""
    if clause_no:
        parts = [p["text"] for p in paragraphs if p.get("clause_no") == clause_no]
        if parts:
            return "\n".join(parts)
    if evidence:
        key = evidence[:8]
        for p in paragraphs:
            if key and key in p["text"]:
                return p["text"]
    return evidence or ""


def assess(
    extracted_clauses: list[dict],
    clause_types: list[dict],
    paragraphs: list[dict] | None = None,
    client=None,
) -> list[dict]:
    """对抽取结果逐条判定，返回与 gold.json 同构的 judgments。

    paragraphs + client 都传入时，对「有正文的条款」启用 LLM 语义判定；
    否则退化为纯规则层（v1 行为）。
    """
    playbook = {t["name"]: t for t in clause_types}
    use_llm = paragraphs is not None and client is not None

    results = []
    for c in extracted_clauses:
        name = c["type"]
        entry = playbook.get(name)

        if not c.get("present"):
            results.append({
                "clause": name,
                "present": False,
                "evidence": "",
                "verdict": "缺失",
                "severity": _MISSING_SEVERITY.get(name, "中"),
                "reason": "全合同无此类条款",
            })
            continue

        # 有正文 + 启用语义层 → LLM 判定
        if use_llm:
            clause_text = _find_clause_text(paragraphs, c.get("clause_no"), c.get("evidence"))
            try:
                r = judge_clause(name, clause_text, entry, client)
                verdict = r.get("verdict", "偏离")
                results.append({
                    "clause": name,
                    "present": True,
                    "evidence": clause_text[:60],
                    "verdict": verdict,
                    "severity": r.get("severity", "中"),
                    "reason": r.get("reason", ""),
                })
                continue
            except Exception:  # noqa: BLE001
                pass  # LLM 失败则回退规则层

        # 规则层兜底：偏离
        results.append({
            "clause": name,
            "present": True,
            "evidence": c.get("evidence", ""),
            "verdict": "偏离",
            "severity": "中",
            "reason": "条款存在，但关键要素留空待填或不完整",
        })
    return results
