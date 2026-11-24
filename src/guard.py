"""前置拦截（Input Guardrails）：域外检测 + 拒答。

两层：
1. 检索阈值（零成本）：BM25 top 分 < LOW → 直接拒答，不调 LLM；
2. 意图分类（1 次小调用）：灰区问题交给 LLM 判断是否属于合同/法律范围。

命中拒答时返回固定文案，不进入生成。
"""

from __future__ import annotations

import json

import config
from src import auth

LOW = 5.0   # 低于此分：直接拒答（零成本）
HIGH = 8.0  # 高于此分：直接放行（不调分类器）

REFUSAL = (
    "这个问题不在当前合同 / 法律的范围内，我无法回答。\n\n"
    "我主要回答与合同条款相关的问题，例如：付款方式、违约金、交付与验收、争议解决、保密与知识产权等。"
)

_CLASSIFY_PROMPT = """判断下面的问题是否与「合同条款 / 法律条文」相关。
只输出 JSON：{{"in_scope": true}} 或 {{"in_scope": false}}

问题：{q}"""

# 命中这些词直接放行（避免"跟我讲讲高风险"这类元问题被误杀）
_SCOPE_KEYWORDS = (
    "风险", "条款", "合同", "审查", "建议", "问题", "付款", "违约金", "交付",
    "验收", "保密", "知识产权", "争议", "解除", "终止", "违约", "责任", "赔偿",
    "甲方", "乙方", "履行", "发票", "竞业", "不可抗力", "数据", "金额", "期限",
)


def _has_scope_keyword(question: str) -> bool:
    return any(k in question for k in _SCOPE_KEYWORDS)


def classify_question(question: str, client) -> bool:
    """意图分类：问题是否属于合同/法律范围。失败时放行（避免误杀正常问题）。"""
    try:
        resp = client.chat.completions.create(
            model=config.MODEL,
            messages=[{"role": "user", "content": _CLASSIFY_PROMPT.format(q=question)}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        return bool(data.get("in_scope", True))
    except Exception:  # noqa: BLE001
        return True


def _cfg() -> tuple[bool, float, float]:
    """读取管理员配置：开关 / 低阈值 / 高阈值。"""
    on = auth.get_setting("guard_on", "1") == "1"
    try:
        low = float(auth.get_setting("guard_low", str(LOW)) or LOW)
        high = float(auth.get_setting("guard_high", str(HIGH)) or HIGH)
    except ValueError:
        low, high = LOW, HIGH
    return on, low, high


def check_scope(
    question: str, hits: list[dict], client, low: float | None = None, high: float | None = None
) -> tuple[bool, str]:
    """返回 (是否放行, 说明)。low/high 可针对不同语料调整。"""
    on, cfg_low, cfg_high = _cfg()
    if not on:
        return True, "拦截已关闭（管理员配置）"

    if _has_scope_keyword(question):
        return True, "命中范围关键词（放行）"

    low = cfg_low if low is None else low
    high = cfg_high if high is None else high
    top = float(hits[0]["score"]) if hits else 0.0
    if top < low:
        return False, f"检索阈值：相关度过低（{top:.1f} < {low}）"
    if top >= high:
        return True, f"检索阈值：相关度高（{top:.1f}）"
    if classify_question(question, client):
        return True, f"意图分类：范围内（检索 {top:.1f}，灰区）"
    return False, f"意图分类：超出范围（检索 {top:.1f}，灰区）"
