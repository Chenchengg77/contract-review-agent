"""LLM-as-judge：用独立的 LLM 评判风险判定结果，用于评估集校准。

用途：评估集（gold.json）是由人/规则标注的，用另一个 LLM 独立评判同样的条款，
      计算两者一致率（Cohen's κ）。κ >= 0.8 说明评估集可信、judge 可用。

注意：judge 用的是「标准要求」（playbook）做依据，不是凭感觉。
"""

from __future__ import annotations

import json

import config


def build_judge_prompt(clause_name: str, evidence: str, entry: dict) -> str:
    """构造 judge prompt：条款类型 + 标准要求 + 合同原文。"""
    must = "、".join(entry.get("must_contain", [])) or "（无）"
    red = "、".join(entry.get("red_flags", [])) or "（无）"
    if evidence:
        contract_text = evidence
    else:
        contract_text = "（该合同未出现此条款，应为“缺失”）"
    return f"""你是资深合同审查专家。请判断下面这份合同的「{clause_name}」相对标准要求的风险状态。

【标准要求】
- 标准条款：{entry.get('standard_text', '')}
- 必含要素：{must}
- 红线：{red}

【合同原文】
{contract_text}

请只返回 JSON（不要解释）：
{{"verdict":"偏离","severity":"中","reason":"一句话说明依据"}}

verdict 只能取：合规（完整覆盖标准）/ 偏离（存在但缺要素或留空）/ 缺失（合同无此条款）/ 冲突（命中红线）
severity 只能取：高 / 中 / 低"""


def judge_clause(clause_name: str, evidence: str, entry: dict, client) -> dict:
    """让 judge 评判单条条款，返回 {verdict, severity, reason}。"""
    prompt = build_judge_prompt(clause_name, evidence, entry)
    resp = client.chat.completions.create(
        model=config.MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)
