"""向量检索 / 重排：降级行为与融合排序（不访问网络，用假编码器）。"""

import config
from src import embed
from src.retrieve import HybridIndex, make_index, rrf_fuse


def test_disabled_without_key(monkeypatch):
    monkeypatch.setattr(config, "EMBEDDING_API_KEY", "")
    monkeypatch.setattr(config, "EMBEDDING_BASE_URL", "https://api.example.com/v1")
    assert embed.enabled() is False
    assert type(make_index()).__name__ == "BM25Index"


def test_requires_both_key_and_base_url(monkeypatch):
    monkeypatch.setattr(config, "EMBEDDING_API_KEY", "sk-test")
    monkeypatch.setattr(config, "EMBEDDING_BASE_URL", "")
    assert embed.enabled() is False


def test_enabled_when_configured(monkeypatch):
    monkeypatch.setattr(config, "EMBEDDING_API_KEY", "sk-test")
    monkeypatch.setattr(config, "EMBEDDING_BASE_URL", "https://api.example.com/v1")
    assert embed.enabled() is True
    assert type(make_index()).__name__ == "HybridIndex"


def test_rerank_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(config, "EMBEDDING_API_KEY", "")
    assert embed.rerank("q", [{"text": "abc"}]) is None


def test_rrf_prefers_doc_hit_by_both():
    a = [{"text": "x", "meta": {}, "score": 9.0}]
    b = [{"text": "y", "meta": {}, "score": 8.0}, {"text": "x", "meta": {}, "score": 7.0}]
    fused = rrf_fuse([a, b], k=2)
    assert fused[0]["text"] == "x"


def test_hybrid_index_with_stub_encoder(monkeypatch):
    monkeypatch.setattr(config, "EMBEDDING_API_KEY", "sk-test")
    monkeypatch.setattr(config, "EMBEDDING_BASE_URL", "https://api.example.com/v1")

    vocab = ["付款", "违约", "保密", "交付"]

    def fake_encode(texts):
        return [[float(t.count(w)) for w in vocab] for t in texts]

    monkeypatch.setattr(embed, "encode", fake_encode)

    idx = HybridIndex()
    idx.add("付款期限为验收后 30 日内", {"id": 1})
    idx.add("违约金为合同总额的 20%", {"id": 2})
    idx.add("双方对保密信息承担保密义务", {"id": 3})

    hits = idx.search("违约金怎么算", k=3)
    assert hits
    assert hits[0]["meta"]["id"] == 2


def test_hybrid_falls_back_when_encoder_fails(monkeypatch):
    monkeypatch.setattr(config, "EMBEDDING_API_KEY", "sk-test")
    monkeypatch.setattr(config, "EMBEDDING_BASE_URL", "https://api.example.com/v1")

    def boom(texts):
        raise RuntimeError("network down")

    monkeypatch.setattr(embed, "encode", boom)

    idx = HybridIndex()
    # 文档要多一点：BM25 在极小语料上 IDF 会退化成 0，测不出召回
    idx.add("付款期限为验收后 30 日内", {"id": 1})
    idx.add("交付地点为甲方指定仓库", {"id": 2})
    idx.add("双方对保密信息承担保密义务", {"id": 3})
    idx.add("质量保证期为验收合格后一年", {"id": 4})
    idx.add("违约金为合同总额的 20%", {"id": 5})
    idx.add("争议提交甲方所在地法院解决", {"id": 6})

    hits = idx.search("违约金", k=3)
    assert hits, "编码失败时应退回 BM25 结果"
    assert hits[0]["meta"]["id"] == 5
