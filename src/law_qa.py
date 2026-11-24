"""法律问答（RAG）：检索法规库 → LLM 基于法条回答 + 引用。

与 qa.py 的区别：
- qa.py 检索「当前合同」的段落（合同问答）；
- 本模块检索「法规库」（法律问答），不绑定具体合同。
"""

from __future__ import annotations

import json

import config
from src.guard import REFUSAL, check_scope
from src.retrieve import BM25Index

_INDEX = None
_ARTICLES = None

_SYSTEM = (
    "你是「法务小助手」，一位有 10 年经验的资深法务，说话专业但温和。\n\n"
    "请严格按以下 Markdown 结构输出（不要偏离）：\n"
    "## 结论\n"
    "（用一句话给出明确结论）\n\n"
    "## 分项说明\n"
    "1. **要点一**：引用《法律名》条号，说明具体规定；\n"
    "2. **要点二**：……\n\n"
    "## 注意事项\n"
    "- （适用条件、例外、风险提示等）\n\n"
    "语气规则：\n"
    "- 用「我」自称、称呼「你」；\n"
    "- 避免「综上所述」「以下是」这类机器人腔；\n"
    "- 不确定时直接说「这条建议找律师确认」。\n\n"
    "事实规则：\n"
    "1. 只根据下面提供的法条回答，没有就说「法规库中没有找到相关条款」，不要编造；\n"
    "2. 引用法条时写明法律名称和条号（如《民法典》第五百七十七条）；\n"
    "3. 不要编造法条之外的规定。"
)


def _load():
    global _INDEX, _ARTICLES
    if _INDEX is None:
        path = config.DATA_DIR / "knowledge" / "laws.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        _ARTICLES = data.get("articles", [])
        _INDEX = BM25Index()
        for a in _ARTICLES:
            text = f"{a['law']} {a['article']} {a['title']} {a['text']}"
            _INDEX.add(text, a)
    return _INDEX, _ARTICLES


def answer_law_question(question: str, client, history: list[dict] | None = None) -> dict:
    """检索法规库 → 拼 prompt → LLM 回答（带法条引用、能拒答）。"""
    idx, _ = _load()
    hits = idx.search(question, k=6)

    # 前置拦截：法规库阈值更低（语料小），灰区交给意图分类
    ok, guard_why = check_scope(question, hits, client, low=3.0, high=6.0)
    if not ok:
        return {
            "answer": REFUSAL,
            "citations": [],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "refused": True,
            "guard": guard_why,
        }

    # 过滤低分噪音：只保留分数接近最高分的前几条
    if hits:
        top = hits[0]["score"] or 1.0
        hits = [h for h in hits if h["score"] >= top * 0.6][:4]

    context = "\n".join(
        f"【{h['meta']['law']} {h['meta']['article']}（{h['meta']['title']}）】{h['meta']['text']}"
        for h in hits
    )
    messages = [{"role": "system", "content": _SYSTEM}]
    for h in (history or [])[-4:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({
        "role": "user",
        "content": f"【相关法条】\n{context}\n\n【用户问题】\n{question}",
    })

    resp = client.chat.completions.create(
        model=config.MODEL,
        messages=messages,
        temperature=0,
        max_tokens=2000,
    )
    usage = {
        "prompt_tokens": resp.usage.prompt_tokens,
        "completion_tokens": resp.usage.completion_tokens,
        "total_tokens": resp.usage.total_tokens,
    }
    citations = [f"{h['meta']['law']} {h['meta']['article']}" for h in hits[:3]]
    return {
        "answer": resp.choices[0].message.content,
        "citations": citations,
        "usage": usage,
        "refused": False,
        "guard": guard_why,
    }


def stream_answer_law_question(question: str, client, history: list[dict] | None = None):
    """流式版本：先发 citations 事件，再逐 token 发 SSE，最后 done。"""
    idx, _ = _load()
    hits = idx.search(question, k=6)

    # 前置拦截（流式版）
    ok, _guard_why = check_scope(question, hits, client, low=3.0, high=6.0)
    if not ok:
        yield f"event: citations\ndata: {json.dumps({'citations': []}, ensure_ascii=False)}\n\n"
        yield f"event: token\ndata: {json.dumps({'text': REFUSAL}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"
        return

    if hits:
        top = hits[0]["score"] or 1.0
        hits = [h for h in hits if h["score"] >= top * 0.6][:4]

    context = "\n".join(
        f"【{h['meta']['law']} {h['meta']['article']}（{h['meta']['title']}）】{h['meta']['text']}"
        for h in hits
    )
    messages = [{"role": "system", "content": _SYSTEM}]
    for h in (history or [])[-4:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({
        "role": "user",
        "content": f"【相关法条】\n{context}\n\n【用户问题】\n{question}",
    })

    citations = [f"{h['meta']['law']} {h['meta']['article']}" for h in hits[:3]]
    yield f"event: citations\ndata: {json.dumps({'citations': citations}, ensure_ascii=False)}\n\n"

    stream = client.chat.completions.create(
        model=config.MODEL,
        messages=messages,
        temperature=0,
        stream=True,
        max_tokens=2000,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield f"event: token\ndata: {json.dumps({'text': delta}, ensure_ascii=False)}\n\n"
    yield "event: done\ndata: {}\n\n"
