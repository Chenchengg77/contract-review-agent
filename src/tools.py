"""问答工具集：让模型在需要精确信息时「主动去查」，而不是只靠一次检索。

四个工具：
- get_clause       按条款名精确取原文（检索可能排不到，但用户明确问某条时很准）
- search_law       查法条库，回答「这样约定合法吗」
- calc_penalty     算违约金 / 逾期利息（模型算数不靠谱，交给代码）
- get_review_summary  取这份合同最近一次审查结论
"""

from __future__ import annotations

import re
from typing import Callable

from src.parser import clause_headings

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_clause",
            "description": "按条款名称读取合同里该条款的完整原文。需要引用具体条款内容时使用（付款、违约金、保密、解除、争议解决等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "clause_name": {"type": "string", "description": "条款名称关键词，如 付款 / 违约金 / 保密 / 解除"},
                },
                "required": ["clause_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_law",
            "description": "检索法规条文（民法典等），返回命中的法条原文。问题涉及「法律怎么规定」「是否合法」「有没有上限」时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "检索关键词，如 违约金 上限 / 定金 / 解除权"},
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calc_penalty",
            "description": "计算违约金或逾期利息。违约金 = 金额 × 比例；逾期利息 = 金额 × 日利率(万分之) × 天数。模型不要自己算，调用这个。",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "金额（元）"},
                    "rate_percent": {"type": "number", "description": "违约金比例（百分数，20 表示 20%）"},
                    "daily_rate": {"type": "number", "description": "日利率（万分之几，5 表示每日万分之五）"},
                    "days": {"type": "number", "description": "逾期天数"},
                },
                "required": ["amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_review_summary",
            "description": "读取这份合同最近一次审查的结论（哪些条款高风险/中风险、判定理由）。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _clean_name(name: str) -> str:
    return re.sub(r"(条款|条|项|约定)$", "", (name or "").strip())


def _full_text(paragraphs: list[dict], idx: int, limit: int = 700) -> str:
    """从第 idx 段开始，取到下一个条款标题之前，截断到 limit。"""
    parts: list[str] = []
    for p in paragraphs[idx:]:
        text = (p.get("text") or "").strip()
        if not text:
            continue
        if parts and p.get("clause_no"):
            break
        parts.append(text)
        if sum(len(x) for x in parts) >= limit:
            break
    return "\n".join(parts)[:limit]


def _tool_get_clause(paragraphs: list[dict], args: dict) -> str:
    name = _clean_name(args.get("clause_name", ""))
    if not name:
        return "没有提供条款名称"

    heads = clause_headings(paragraphs)
    # ① 标题里包含关键词
    for h in heads:
        if name in (h.get("text") or ""):
            i = paragraphs.index(h)
            return _full_text(paragraphs, i) or f"找到「{h.get('clause_no', '')}」但内容为空"

    # ② 正文里包含关键词：取第一次出现的段落及其后文
    for i, p in enumerate(paragraphs):
        if name in (p.get("text") or ""):
            return _full_text(paragraphs, i, limit=500)

    return f"合同里没有找到与「{name}」相关的条款"


def _tool_search_law(args: dict) -> str:
    from src import law_qa

    keyword = (args.get("keyword") or "").strip()
    if not keyword:
        return "没有提供检索关键词"
    idx, _ = law_qa._load()
    hits = idx.search(keyword, k=3)
    if not hits:
        return f"法规库里没有与「{keyword}」相关的条文"
    lines = []
    for h in hits:
        m = h["meta"]
        lines.append(f"《{m.get('law', '')}》{m.get('article', '')}（{m.get('title', '')}）：{m.get('text', '')}")
    return "\n\n".join(lines)


def _tool_calc_penalty(args: dict) -> str:
    try:
        amount = float(args.get("amount") or 0)
    except (TypeError, ValueError):
        return "金额格式不对"
    if amount <= 0:
        return "金额必须大于 0"

    out = []
    rate = args.get("rate_percent")
    if rate not in (None, ""):
        try:
            r = float(rate)
            out.append(f"违约金 = {amount:,.2f} × {r}% = **{amount * r / 100:,.2f} 元**")
        except (TypeError, ValueError):
            pass

    daily = args.get("daily_rate")
    days = args.get("days")
    if daily not in (None, "") and days not in (None, ""):
        try:
            d = float(daily)
            n = float(days)
            out.append(
                f"逾期利息 = {amount:,.2f} × 万分之 {d} × {n:g} 天 = **{amount * d / 10000 * n:,.2f} 元**"
            )
        except (TypeError, ValueError):
            pass

    if not out:
        return "需要提供 rate_percent，或 daily_rate + days"
    return "\n".join(out)


def build_executor(
    paragraphs: list[dict],
    review_text: str = "",
) -> Callable[[str, dict], str]:
    """返回 (name, args) -> 字符串 的派发器。"""

    def _dispatch(name: str, args: dict) -> str:
        try:
            if name == "get_clause":
                return _tool_get_clause(paragraphs, args or {})
            if name == "search_law":
                return _tool_search_law(args or {})
            if name == "calc_penalty":
                return _tool_calc_penalty(args or {})
            if name == "get_review_summary":
                return review_text or "这份合同还没有审查记录"
            return f"未知工具：{name}"
        except Exception as e:  # noqa: BLE001
            return f"工具执行出错：{e}"

    return _dispatch
