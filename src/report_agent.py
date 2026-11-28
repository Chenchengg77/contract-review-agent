"""报告依据：把 playbook 的规则翻译成「判定依据」，附在每条判定上。

三层依据（全部来自 `data/playbook/clauses.json`，纯代码组装，不经过大模型）：
1. **必备要素**（must_contain）—— 这类条款应该写清什么
2. **判定红线**（red_flags）—— 哪些写法直接算风险
3. **示范条款**（standard_text）—— 标准写法长什么样

外加可选的「法律参考」：只在本地法条库中**确有可靠映射**时才给（宁缺勿错）。

因为不调用模型，所以：零额外成本、零幻觉、13 类条款全覆盖。
"""

from __future__ import annotations

import json

import config

# 条款 → 法条（人工映射；库只有 28 条，检索容易错配，所以不用检索）
_CLAUSE_TO_LAW: dict[str, tuple[str, str]] = {
    "违约责任": ("民法典", "第五百七十七条"),
    "违约金": ("民法典", "第五百八十五条"),
    "责任上限": ("民法典", "第五百八十五条"),
    "损失赔偿": ("民法典", "第五百八十四条"),
    "合同解除": ("民法典", "第五百六十三条"),
    "解除": ("民法典", "第五百六十三条"),
    "合同终止": ("民法典", "第五百六十三条"),
    "不可抗力": ("民法典", "第五百九十条"),
    "争议解决": ("民法典", "第四百七十条"),
    "格式条款": ("民法典", "第四百九十六条"),
}


def law_ref(clause: str) -> dict | None:
    """按映射查法条库，返回真实存在的条文；没有可靠对应就返回 None。"""
    mapping = _CLAUSE_TO_LAW.get(clause)
    if not mapping:
        return None
    law_kw, article = mapping
    try:
        data = json.loads(
            (config.DATA_DIR / "knowledge" / "laws.json").read_text(encoding="utf-8")
        )
    except Exception:  # noqa: BLE001
        return None
    for a in data.get("articles", []):
        if a.get("article") == article and law_kw in (a.get("law") or ""):
            return {
                "law": a.get("law", ""),
                "article": a.get("article", ""),
                "title": a.get("title", ""),
                "text": (a.get("text") or "")[:160],
            }
    return None


def build_basis(judgments: list[dict], clause_types: list[dict]) -> int:
    """给「非合规」的判定挂上 `basis` 字段，返回附上依据的条数。"""
    playbook = {t.get("name"): t for t in clause_types or []}
    attached = 0
    for j in judgments:
        if j.get("verdict") == "合规":
            continue
        entry = playbook.get(j.get("clause")) or {}
        basis = {
            "must_contain": entry.get("must_contain") or [],
            "red_flags": entry.get("red_flags") or [],
            "standard_text": entry.get("standard_text") or "",
        }
        ref = law_ref(j.get("clause", ""))
        if ref:
            basis["legal_ref"] = ref
        if basis["must_contain"] or basis["red_flags"] or basis["standard_text"]:
            j["basis"] = basis
            attached += 1
    return attached
