"""合同问答（RAG）：检索合同相关段落 → LLM 基于原文回答 + 引用。

对应 Day4（RAG v1）：检索 → 拼接 → 生成 → 引用。
"""

from __future__ import annotations

import json
from pathlib import Path

import config
from src.guard import REFUSAL, check_scope
from src.parser import parse
from src.retrieve import BM25Index

_SYSTEM = (
    "你是「法务小助手」，一位有 10 年经验的合同审查法务，说话专业但温和。\n"
    "语气规则：\n"
    "1. 用「我」自称，称呼对方为「你」；\n"
    "2. 先说结论，再说原因，最后给建议；\n"
    "3. 不要用「综上所述」「以下是」「首先/其次/最后」这类机器人腔；\n"
    "4. 不确定时直接说「这条建议找律师确认」，不要装懂；\n"
    "5. 风险高时提醒一句「这条要小心」。\n\n"
    "事实规则：\n"
    "6. 只根据下面提供的合同原文回答，没写就说「合同里没写这条」，不要编造；\n"
    "7. 如果提供了「审查结果摘要」，可以直接用它回答「哪条高风险」这类问题；\n"
    "8. 引用条款号（如「第八条」）；\n"
    "9. 回答简洁，2~4 句话。"
)


def _build_context(hits: list[dict]) -> str:
    parts = []
    for h in hits:
        label = h["meta"].get("clause_no") or "正文"
        parts.append(f"[{label}] {h['text']}")
    return "\n".join(parts)


def answer_question(
    path: Path,
    question: str,
    client,
    history: list[dict] | None = None,
    review_ctx: str = "",
) -> dict:
    """检索合同 → 前置拦截 → 拼 prompt → LLM 回答（带引用、能拒答）。"""
    paragraphs = parse(path)
    idx = BM25Index()
    for p in paragraphs:
        idx.add(p["text"], p)
    hits = idx.search(question, k=6)

    # 前置拦截：越界问题直接拒答，不调 LLM（省钱、快、提示明确）
    ok, guard_why = check_scope(question, hits, client)
    if not ok:
        return {
            "answer": REFUSAL,
            "citations": [],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "refused": True,
            "guard": guard_why,
        }

    context = _build_context(hits)
    messages = [{"role": "system", "content": _SYSTEM}]
    for h in (history or [])[-4:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({
        "role": "user",
        "content": (f"【审查结果摘要】\n{review_ctx}\n\n" if review_ctx else "")
        + f"【合同原文片段】\n{context}\n\n【用户问题】\n{question}",
    })

    resp = client.chat.completions.create(
        model=config.MODEL,
        messages=messages,
        temperature=0,
    )
    answer = resp.choices[0].message.content
    usage = {
        "prompt_tokens": resp.usage.prompt_tokens,
        "completion_tokens": resp.usage.completion_tokens,
        "total_tokens": resp.usage.total_tokens,
    }
    citations = sorted({h["meta"].get("clause_no") or "正文" for h in hits})
    return {"answer": answer, "citations": citations, "usage": usage, "refused": False, "guard": guard_why}


def stream_answer_question(
    path: Path,
    question: str,
    client,
    history: list[dict] | None = None,
    review_ctx: str = "",
):
    """流式版本：先发 citations 事件，再逐 token 发 SSE，最后 done。"""
    paragraphs = parse(path)
    idx = BM25Index()
    for p in paragraphs:
        idx.add(p["text"], p)
    hits = idx.search(question, k=6)

    # 前置拦截：越界直接拒答，不进入生成
    ok, _guard_why = check_scope(question, hits, client)
    if not ok:
        yield f"event: citations\ndata: {json.dumps({'citations': []}, ensure_ascii=False)}\n\n"
        yield f"event: token\ndata: {json.dumps({'text': REFUSAL}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"
        return

    context = _build_context(hits)
    messages = [{"role": "system", "content": _SYSTEM}]
    for h in (history or [])[-4:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({
        "role": "user",
        "content": (f"【审查结果摘要】\n{review_ctx}\n\n" if review_ctx else "")
        + f"【合同原文片段】\n{context}\n\n【用户问题】\n{question}",
    })

    citations = sorted({h["meta"].get("clause_no") or "正文" for h in hits})
    yield f"event: citations\ndata: {json.dumps({'citations': citations}, ensure_ascii=False)}\n\n"

    stream = client.chat.completions.create(
        model=config.MODEL,
        messages=messages,
        temperature=0,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield f"event: token\ndata: {json.dumps({'text': delta}, ensure_ascii=False)}\n\n"
    yield "event: done\ndata: {}\n\n"
