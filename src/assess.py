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
import re

import config
from src.judge import judge_clause

# 主条款：第X条 / 第X章 / 一、；小节（1.1 / 1. / （一））不算边界
_MAIN_CLAUSE_RE = re.compile(r"^(第[一二三四五六七八九十百零0-9]+[条章]|[一二三四五六七八九十]+、)")

_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _cn_to_int(s: str) -> int | None:
    """中文数字转 int（支持 1~99）。"""
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if "十" in s:
        a, b = s.split("十", 1)
        tens = _CN_NUM.get(a, 1) if a else 1
        ones = _CN_NUM.get(b, 0) if b else 0
        return tens * 10 + ones
    return _CN_NUM.get(s)


def _clause_key(clause_no: str | None) -> str:
    """把「第十条」「10」「10.」「一、」统一成数字字符串，便于跨格式匹配。"""
    s = (clause_no or "").strip()
    if not s:
        return ""
    m = re.match(r"^第([一二三四五六七八九十百零〇0-9]+)[条章]", s)
    if m:
        v = _cn_to_int(m.group(1))
        return str(v) if v is not None else s
    m2 = re.match(r"^([一二三四五六七八九十]+)、", s)
    if m2:
        v = _cn_to_int(m2.group(1))
        return str(v) if v is not None else s
    m3 = re.match(r"^(\d+)", s)
    if m3:
        return str(int(m3.group(1)))
    return s

# 缺失时判定为「高」风险的条款类型（与 playbook 的 severity_rule 一致）
_MISSING_SEVERITY = {
    "付款条款": "高", "违约金": "高", "争议解决": "高",
    "保密条款": "高", "知识产权": "高", "责任上限": "高",
}


def load_playbook() -> list[dict]:
    data = json.loads((config.PLAYBOOK_DIR / "clauses.json").read_text(encoding="utf-8"))
    return data["clause_types"]


def _collect_body(paragraphs: list[dict], i: int) -> str:
    """从第 i 段开始收集正文，直到下一个「主条款」或「数字编号条款」为止。"""
    parts = [paragraphs[i]["text"]]
    for q in paragraphs[i + 1:]:
        if _MAIN_CLAUSE_RE.match(q.get("clause_no") or ""):
            break
        t = (q.get("text") or "").strip()
        # 「10. xxx」「3、xxx」这类编号段落也是新条款的开始
        if t and re.match(r"^\d+[\.、]", t):
            break
        if t:
            parts.append(t)
    return "\n".join(parts)


def _find_clause_text(paragraphs: list[dict], clause_no: str, evidence: str) -> str:
    """从段落里找该条款的完整正文：条款号所在段 + 其后的正文段（直到下一个主条款）。

    两段式匹配（避免「第二条」误匹配附件里的「2.《机动车行驶证》」）：
    1. 精确：段落文本以该条款号开头（如「第二条」「10.」）；
    2. 回退：条款号归一化成数字后一致，且段落以数字编号开头。
    """
    best = ""
    if clause_no:
        # ① 精确前缀匹配
        for i, p in enumerate(paragraphs):
            t = (p.get("text") or "").strip()
            if t and t.startswith(clause_no):
                body = _collect_body(paragraphs, i)
                if len(body) > len(best):
                    best = body
        if best:
            return best

        # ② 数字归一化回退（只认「10.」「10、」这类编号开头）
        key = _clause_key(clause_no)
        for i, p in enumerate(paragraphs):
            t = (p.get("text") or "").strip()
            if not t or not re.match(r"^\d+[\.、]", t):
                continue
            if _clause_key(t[:4]) != key:
                continue
            body = _collect_body(paragraphs, i)
            if len(body) > len(best):
                best = body
        if best:
            return best

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
    perspective: str = "",
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
                r = judge_clause(name, clause_text, entry, client, perspective)
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
