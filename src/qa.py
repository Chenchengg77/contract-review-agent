"""合同问答（RAG）：检索合同相关段落 → LLM 基于原文回答 + 引用。

对应 Day4（RAG v1）：检索 → 拼接 → 生成 → 引用。
"""

from __future__ import annotations

from pathlib import Path

import config
from src.parser import parse
from src.retrieve import BM25Index

_SYSTEM = (
    "你是合同审查助手。请**只根据下面提供的合同原文**回答用户问题。\n"
    "规则：\n"
    "1. 如果合同原文里没有相关信息，直接回答「合同里没有找到相关内容」，不要编造；\n"
    "2. 回答时引用条款号（如「第八条」）；\n"
    "3. 回答简洁，2~4 句话。"
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
) -> dict:
    """检索合同 → 拼 prompt → LLM 回答（带引用、能拒答）。"""
    paragraphs = parse(path)
    idx = BM25Index()
    for p in paragraphs:
        idx.add(p["text"], p)
    hits = idx.search(question, k=6)

    context = _build_context(hits)
    messages = [{"role": "system", "content": _SYSTEM}]
    for h in (history or [])[-4:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({
        "role": "user",
        "content": f"【合同原文片段】\n{context}\n\n【用户问题】\n{question}",
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
    return {"answer": answer, "citations": citations, "usage": usage}
