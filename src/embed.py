"""向量检索 + 重排（API 方案，OpenAI 兼容接口）。

设计原则：
- **可选增强**：没配 EMBEDDING_API_KEY 时整个模块自动禁用，检索退回 BM25，不影响任何功能；
- **失败不炸**：接口超时/报错时降级为「返回原始顺序」，不抛异常打断问答；
- **结果缓存**：同一段文本只编码一次（进程内缓存），合同问答场景重复率高。

推荐配置（硅基流动为例）：
    EMBEDDING_API_KEY=sk-xxx
    EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
    EMBEDDING_MODEL=BAAI/bge-m3
    RERANK_MODEL=BAAI/bge-reranker-v2-m3
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.request

import config

_CACHE: dict[str, list[float]] = {}
TIMEOUT = 20


def enabled() -> bool:
    """是否启用向量检索（有 key 且配了 base url）。"""
    return bool(config.EMBEDDING_API_KEY and config.EMBEDDING_BASE_URL)


def _post(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.EMBEDDING_API_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def encode(texts: list[str]) -> list[list[float]]:
    """批量编码；失败抛异常，由调用方决定降级。"""
    if not texts:
        return []
    base = config.EMBEDDING_BASE_URL.rstrip("/")
    data = _post(
        f"{base}/embeddings",
        {"model": config.EMBEDDING_MODEL, "input": texts},
    )
    items = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
    return [it["embedding"] for it in items]


def _key(text: str) -> str:
    return hashlib.sha1(f"{config.EMBEDDING_MODEL}:{text}".encode("utf-8")).hexdigest()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def rerank(query: str, docs: list[dict], top_n: int = 5) -> list[dict] | None:
    """调 rerank 接口重排；不可用或失败返回 None（调用方保持原顺序）。"""
    if not enabled() or not docs:
        return None
    base = config.EMBEDDING_BASE_URL.rstrip("/")
    try:
        data = _post(
            f"{base}/rerank",
            {
                "model": config.RERANK_MODEL,
                "query": query,
                "documents": [d["text"] for d in docs],
                "top_n": top_n,
            },
        )
    except Exception:  # noqa: BLE001
        return None
    results = data.get("results") or []
    out = []
    for r in results:
        i = r.get("index")
        if isinstance(i, int) and 0 <= i < len(docs):
            out.append({**docs[i], "rerank_score": round(float(r.get("relevance_score", 0)), 4)})
    return out or None


class VectorIndex:
    """极简向量索引：文档量小（单份合同几十段），直接暴力算余弦。"""

    def __init__(self) -> None:
        self._docs: list[str] = []
        self._meta: list[dict] = []
        self._vecs: list[list[float]] = []
        self.failed = False

    def add(self, text: str, meta: dict) -> None:
        self._docs.append(text)
        self._meta.append(meta)

    def build(self) -> bool:
        """懒构建：把还没编码的文档补上。返回是否可用。"""
        if len(self._vecs) >= len(self._docs):
            return True
        if not enabled():
            self.failed = True
            return False
        need = self._docs[len(self._vecs):]
        try:
            vecs = encode(need)
        except Exception:  # noqa: BLE001
            self.failed = True
            return False
        if len(vecs) != len(need):
            self.failed = True
            return False
        self._vecs.extend(vecs)
        return True

    def search(self, query: str, k: int = 5) -> list[dict]:
        if not self.build() or not self._vecs:
            return []
        try:
            qv = _CACHE.get(_key(query)) or encode([query])[0]
        except Exception:  # noqa: BLE001
            return []
        _CACHE[_key(query)] = qv
        scored = [(i, _cosine(qv, v)) for i, v in enumerate(self._vecs)]
        scored.sort(key=lambda x: -x[1])
        return [
            {"text": self._docs[i], "meta": self._meta[i], "score": round(s, 4)}
            for i, s in scored[:k]
            if s > 0.05
        ]

    def __len__(self) -> int:
        return len(self._docs)
