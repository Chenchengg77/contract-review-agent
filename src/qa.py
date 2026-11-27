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
from src.tools import TOOLS, build_executor

MAX_TOOL_ROUNDS = 3

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


def _cite(hit: dict) -> str:
    """条款号去掉尾部的顿号/点，避免「五、、第六条」这种拼接。"""
    label = (hit.get("meta", {}).get("clause_no") or "").strip().rstrip("、.．,，")
    return label or "正文"


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
    citations = sorted({_cite(h) for h in hits})
    return {"answer": answer, "citations": citations, "usage": usage, "refused": False, "guard": guard_why}


def _build_messages(
    context: str, question: str, history: list[dict] | None, review_ctx: str
) -> list[dict]:
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
    return messages


def _run_tool_loop(client, messages: list[dict], executor) -> tuple[str, list[dict], dict]:
    """工具调用循环：返回 (最终回答, 调用过的工具, 累计 usage)。"""
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    tools_used: list[dict] = []
    answer = ""

    def _acc(r):
        if getattr(r, "usage", None):
            usage["prompt_tokens"] += r.usage.prompt_tokens or 0
            usage["completion_tokens"] += r.usage.completion_tokens or 0
            usage["total_tokens"] += r.usage.total_tokens or 0

    for _ in range(MAX_TOOL_ROUNDS):
        resp = client.chat.completions.create(
            model=config.MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0,
        )
        _acc(resp)
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            answer = msg.content or ""
            break

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })
        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = executor(name, args)
            tools_used.append({"name": name, "args": args})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    if not answer:
        resp = client.chat.completions.create(
            model=config.MODEL, messages=messages, temperature=0
        )
        _acc(resp)
        answer = resp.choices[0].message.content or ""
    return answer, tools_used, usage


def answer_with_tools(
    path: Path,
    question: str,
    client,
    history: list[dict] | None = None,
    review_ctx: str = "",
) -> dict:
    """工具调用版问答：模型可主动 get_clause / search_law / calc_penalty / get_review_summary。

    仍然先过前置护栏；工具只读、只查这份合同或法条库。
    """
    paragraphs = parse(path)
    idx = BM25Index()
    for p in paragraphs:
        idx.add(p["text"], p)
    hits = idx.search(question, k=6)

    ok, guard_why = check_scope(question, hits, client)
    if not ok:
        return {
            "answer": REFUSAL,
            "citations": [],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "refused": True,
            "guard": guard_why,
            "tools_used": [],
        }

    context = _build_context(hits)
    messages = _build_messages(context, question, history, review_ctx)
    executor = build_executor(paragraphs, review_ctx)

    try:
        answer, tools_used, usage = _run_tool_loop(client, messages, executor)
    except Exception:
        # 模型/网关不支持 tool calling：退回普通 RAG 回答
        return answer_question(path, question, client, history, review_ctx)

    citations = sorted({_cite(h) for h in hits})
    return {
        "answer": answer,
        "citations": citations,
        "usage": usage,
        "refused": False,
        "guard": guard_why,
        "tools_used": tools_used,
    }


def stream_answer_with_tools(
    path: Path,
    question: str,
    client,
    history: list[dict] | None = None,
    review_ctx: str = "",
):
    """流式 + 工具调用：先跑工具循环，再分片下发答案，并告知用了哪些工具。"""
    paragraphs = parse(path)
    idx = BM25Index()
    for p in paragraphs:
        idx.add(p["text"], p)
    hits = idx.search(question, k=6)

    ok, _guard_why = check_scope(question, hits, client)
    if not ok:
        yield f"event: citations\ndata: {json.dumps({'citations': []}, ensure_ascii=False)}\n\n"
        yield f"event: token\ndata: {json.dumps({'text': REFUSAL}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"
        return

    context = _build_context(hits)
    messages = _build_messages(context, question, history, review_ctx)
    executor = build_executor(paragraphs, review_ctx)

    try:
        answer, tools_used, usage = _run_tool_loop(client, messages, executor)
    except Exception:
        # 不支持 tool calling：退回普通流式问答
        yield from stream_answer_question(path, question, client, history, review_ctx)
        return

    citations = sorted({_cite(h) for h in hits})
    yield f"event: tools\ndata: {json.dumps({'tools': tools_used}, ensure_ascii=False)}\n\n"
    yield f"event: citations\ndata: {json.dumps({'citations': citations}, ensure_ascii=False)}\n\n"

    for i in range(0, len(answer), 12):
        yield f"event: token\ndata: {json.dumps({'text': answer[i:i + 12]}, ensure_ascii=False)}\n\n"
    yield f"event: done\ndata: {json.dumps({'usage': usage}, ensure_ascii=False)}\n\n"


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

    citations = sorted({_cite(h) for h in hits})
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
