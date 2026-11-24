"""条款修订建议生成：对偏离/冲突条款，生成修订后的条款文本。

输入：条款名 + 原条款文本 + playbook 标准（standard_text / must_contain / red_flags）
输出：一段可直接替换原条款的修订文本。
"""

from __future__ import annotations

import config


def generate_revision(
    clause_name: str,
    clause_text: str,
    entry: dict,
    client,
    focus: str = "",
    perspective: str = "",
) -> str:
    """基于标准要求，生成修订后的条款文本。focus 关注点，perspective 审查立场。"""
    must = "、".join(entry.get("must_contain", [])) or "（无）"
    red = "、".join(entry.get("red_flags", [])) or "（无）"
    focus_line = f"\n【审查关注点】{focus}" if focus else ""
    stance_line = (
        f"\n【审查立场】{perspective}：修订后的条款应在合规前提下，适度有利于{perspective}。"
        if perspective
        else ""
    )
    prompt = f"""你是资深合同审查专家。下面这份合同的「{clause_name}」条款存在风险，请生成一份修订后的条款文本。

【标准条款参考】{entry.get('standard_text', '')}
【必含要素】{must}
【需要避免的红线】{red}{focus_line}{stance_line}

【原条款】
{clause_text or '（该条款缺失或留空）'}

要求：
1. 只输出修订后的条款文本（一段话，可直接替换原条款），不要解释，不要加引号；
2. 未知的具体数值、日期、比例统一用 ___ 占位，不要用【】或其它符号；
3. 相对原条款新增或调整的内容，在对应句子前加「【新增】」标注（便于对比改了哪里）；
4. 若原条款完全缺失或为空白，则直接给出完整条款，不要加【新增】标注。"""

    resp = client.chat.completions.create(
        model=config.MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()
