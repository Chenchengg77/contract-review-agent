"""条款抽取模块。

从 parser 的结构化段落里，用 LLM 抽出 13 类条款，并强制输出原文引用（evidence），
抽取后做「原文可搜」校验，防止模型编造条款位置。

对应 Day2 结构化输出 + Day4 引用校验。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from openai import OpenAI

import config

PLAYBOOK_PATH = config.DATA_DIR / "playbook" / "clauses.json"

# 每类条款的「识别关键词」，用于 prompt 提示 LLM 该找什么（比 standard_text 更直接）
HINTS = {
    "付款条款": "付款、结算、价款、租金、报酬、费用支付",
    "违约金": "违约责任、违约金、逾期",
    "争议解决": "争议、纠纷、仲裁、诉讼",
    "保密条款": "保密、商业秘密",
    "知识产权": "知识产权、著作权、专利",
    "合同终止": "解除、终止、提前通知",
    "责任上限": "责任上限、赔偿上限、间接损失",
    "验收条款": "验收、检验标准、异议期限",
    "交付条款": "交付、交货、交（提）货、移交",
    "发票条款": "发票、税率、开票",
    "竞业限制": "竞业、同业竞争",
    "数据合规": "数据、个人信息、信息安全",
    "不可抗力": "不可抗力、免责",
}


def load_clause_types() -> list[dict]:
    """从 playbook 加载 13 类条款定义（name + standard_text）。"""
    data = json.loads(PLAYBOOK_PATH.read_text(encoding="utf-8"))
    return data["clause_types"]


def make_client() -> OpenAI:
    """按 config 构造 OpenAI 兼容客户端（DeepSeek）。"""
    return OpenAI(
        api_key=config.require_api_key(),
        base_url=config.DEEPSEEK_BASE_URL,
    )


def _normalize(s: str) -> str:
    """去掉所有空白，用于「原文可搜」子串比对。"""
    return re.sub(r"\s+", "", s or "")


def _format_contract(paragraphs: list[dict], max_chars: int = 12000) -> str:
    """把结构化段落格式化成带【序号】的文本块；超长时截断（条款标题优先保留）。"""
    lines = []
    total = 0
    for p in paragraphs:
        text = p["text"]
        # 有条款号的段落是标题，保留更长的内容；正文段落截短
        keep = 120 if p["clause_no"] else 80
        line = f"【{p['id']}】{text[:keep]}"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)


def build_prompt(paragraphs: list[dict], clause_types: list[dict]) -> str:
    """构造抽取 prompt：13 类定义 + 合同全文 + JSON 输出要求。"""
    type_desc = "\n".join(
        f"{i + 1}. {t['name']}（找：{HINTS.get(t['name'], t['name'])}）"
        for i, t in enumerate(clause_types)
    )
    contract_text = _format_contract(paragraphs)
    return f"""你是合同审查助手。请判断下面这份合同中，以下 {len(clause_types)} 类条款是否存在，并逐字引用原文。

【条款类型】
{type_desc}

【合同文本】（每行以【序号】开头）
{contract_text}

请只返回 JSON（不要任何解释文字），格式如下：
{{"clauses":[{{"type":"违约金","present":true,"clause_no":"第十条","evidence":"第十条 违约责任","confidence":0.9}}]}}

要求：
1. type 必须使用上面【条款类型】里的名称，一个字都不能改；
2. present=true 表示「合同里出现了这类条款的标题」，即使标题后面内容是空白的、留空待填的，也照样算 present=true（留空只是待当事人填写，条款本身仍然存在）；
   只有整份合同完全找不到这类条款的标题时，present 才为 false；
3. present=true 时，evidence 必须逐字摘自合同原文（通常就是该条款的标题行，例如"第十条 违约责任"），clause_no 填该条款的条款号（没有条款号则空字符串）；
4. present=false 时，clause_no 和 evidence 都留空字符串 ""；
5. confidence 是 0~1 之间的小数，表示你对 present 判断的把握；
6. {len(clause_types)} 类都要返回，一个不能少。"""


def _parse_json(text: str) -> dict:
    """稳健解析 LLM 返回的 JSON（容错 markdown 代码块）。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def extract(client: OpenAI, paragraphs: list[dict], clause_types: list[dict]):
    """调用 LLM 抽取 13 类条款，返回 (clauses, usage)。"""
    prompt = build_prompt(paragraphs, clause_types)
    resp = client.chat.completions.create(
        model=config.MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    data = _parse_json(resp.choices[0].message.content)
    usage = {
        "prompt_tokens": resp.usage.prompt_tokens,
        "completion_tokens": resp.usage.completion_tokens,
        "total_tokens": resp.usage.total_tokens,
    }
    return data.get("clauses", []), usage


def validate(paragraphs: list[dict], clauses: list[dict]) -> list[dict]:
    """后置校验：present=true 的 evidence 必须能原文搜到，否则置信度归零。

    这是抗幻觉的关键一环——模型说「第X条 有违约金」但原文搜不到，就不算数。
    """
    full = _normalize("\n".join(p["text"] for p in paragraphs))
    for c in clauses:
        ev = c.get("evidence")
        if c.get("present") and ev:
            ok = _normalize(ev) in full
            c["_evidence_ok"] = bool(ok)
            if not ok:
                c["confidence"] = 0.0
        else:
            c["_evidence_ok"] = True
    return clauses
