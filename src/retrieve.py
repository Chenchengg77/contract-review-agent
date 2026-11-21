"""检索模块：对合同条款库做 BM25 + RRF 混合检索。

用途：给「查相似历史条款」「查法规」等工具提供检索能力。
设计分层（重要）：
- 风险判定（Step 9）用「条款类型 -> playbook」直接映射，不走检索；
- 检索只用于「找相似案例/法规」，不用于「猜条款类型」。

对应 Day3（手写检索，不用向量库）+ Day6（RRF 混合）。
向量检索/rerank 预留接口，可后续接入 embedding API。
"""

from __future__ import annotations

import re


def tokenize(text: str) -> list[str]:
    """中文按字切分、英文数字按词切分（简单但够用，无需 jieba）。"""
    text = (text or "").lower()
    return re.findall(r"[\u4e00-\u9fff]|[a-z0-9_]+", text)


class BM25Index:
    """BM25 检索器：文档少，直接重建索引即可。"""

    def __init__(self) -> None:
        self._docs: list[str] = []
        self._meta: list[dict] = []
        self._tokens: list[list[str]] = []
        self._bm25 = None

    def add(self, text: str, meta: dict) -> None:
        self._docs.append(text)
        self._meta.append(meta)
        self._tokens.append(tokenize(text))
        # 惰性重建放到 search 时统一做，避免每次 add 都重建
        self._bm25 = None

    def _ensure_index(self) -> None:
        if self._bm25 is None and self._tokens:
            from rank_bm25 import BM25Okapi
            self._bm25 = BM25Okapi(self._tokens)

    def search(self, query: str, k: int = 5) -> list[dict]:
        self._ensure_index()
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [
            {"text": self._docs[i], "meta": self._meta[i], "score": round(float(scores[i]), 4)}
            for i in ranked if scores[i] > 0
        ]

    def __len__(self) -> int:
        return len(self._docs)


def rrf_fuse(rank_lists: list[list[dict]], k: int = 5, c: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion：融合多个检索器的排序结果。

    输入多个检索器的 top-k 结果，输出融合后的 top-k。
    """
    fused_scores: dict[str, float] = {}
    docs: dict[str, dict] = {}
    for ranking in rank_lists:
        for rank, item in enumerate(ranking):
            key = item["text"]
            fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (c + rank + 1)
            docs[key] = item
    merged = sorted(fused_scores.items(), key=lambda kv: -kv[1])[:k]
    return [dict(docs[key], rrf_score=round(score, 4)) for key, score in merged]


def build_clause_index(contracts: list[tuple[str, list[dict]]]) -> BM25Index:
    """把多份合同的「条款标题 + 正文」建成检索索引。

    contracts: [(合同文件名, parser.parse 的段落列表), ...]
    """
    index = BM25Index()
    for fname, paragraphs in contracts:
        for p in paragraphs:
            text = p["text"].strip()
            if not text:
                continue
            # 优先索引用带条款号的句子（检索价值更高）
            label = (p["clause_no"] + " " + p["heading"]).strip() if p["clause_no"] else p["text"][:40]
            index.add(text, {"file": fname, "clause_no": p["clause_no"], "heading": p["heading"]})
    return index
