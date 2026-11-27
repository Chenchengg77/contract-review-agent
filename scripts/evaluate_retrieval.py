"""检索消融实验：对比 4 种检索策略。

    python scripts/evaluate_retrieval.py

策略：
  bm25        纯关键词（BM25）
  vector      纯语义（bge-m3 向量）
  hybrid      BM25 + 向量，RRF 融合
  hybrid_rr   混合 + rerank 精排（线上默认）

指标：Hit@1 / Hit@3 / Hit@5 / MRR@5 + 库外问题拒答率
输出：results/retrieval_ablation.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import embed as EMB  # noqa: E402
from src.parser import parse  # noqa: E402
from src.retrieve import BM25Index, rrf_fuse  # noqa: E402

GOLD = ROOT / "data" / "eval" / "retrieval_gold.json"
OUT = ROOT / "results" / "retrieval_ablation.json"
TOP_K = 5


def load_gold() -> dict:
    return json.loads(GOLD.read_text(encoding="utf-8"))


def build_cache(cases: list[dict]) -> dict:
    """每份合同只解析一次；BM25 / 向量索引各建一次。"""
    files = sorted({c["file"] for c in cases} | {"租赁_房屋租赁合同.docx"})
    cache = {}
    for f in files:
        paras = [p for p in parse(ROOT / "data" / "raw" / f) if p["text"].strip()]
        bm = BM25Index()
        vec = EMB.VectorIndex()
        for p in paras:
            bm.add(p["text"], p)
            vec.add(p["text"], p)
        cache[f] = {"paras": paras, "bm25": bm, "vec": vec}
    return cache


def search(cache: dict, file: str, q: str, strategy: str) -> list[dict]:
    c = cache[file]
    if strategy == "bm25":
        return c["bm25"].search(q, k=TOP_K)
    if strategy == "vector":
        return c["vec"].search(q, k=TOP_K)

    bm = c["bm25"].search(q, k=TOP_K * 2)
    vc = c["vec"].search(q, k=TOP_K * 2)
    if not vc:
        merged = bm[:TOP_K]
    elif not bm:
        merged = vc[:TOP_K]
    else:
        merged = rrf_fuse([bm, vc], k=TOP_K)

    if strategy == "hybrid_rr":
        rr = EMB.rerank(q, merged, top_n=TOP_K)
        if rr:
            merged = rr
    return merged


def evaluate(strategy: str, cases: list[dict], cache: dict) -> dict:
    hit1 = hit3 = hit5 = 0
    mrr = 0.0
    misses = []
    for c in cases:
        hits = search(cache, c["file"], c["question"], strategy)
        rank = None
        for i, h in enumerate(hits, 1):
            if c["expect"] in h["text"]:
                rank = i
                break
        if rank:
            hit1 += rank <= 1
            hit3 += rank <= 3
            hit5 += rank <= 5
            mrr += 1.0 / rank
        else:
            misses.append({"question": c["question"], "file": c["file"]})
    n = len(cases)
    return {
        "hit@1": round(hit1 / n, 4),
        "hit@3": round(hit3 / n, 4),
        "hit@5": round(hit5 / n, 4),
        "mrr@5": round(mrr / n, 4),
        "misses": misses,
    }


def refusal_rate(cache: dict, out_of_scope: list[str], use_guard: bool = True) -> dict:
    """库外问题：走真实护栏（阈值 + 灰区意图分类），看最终是否拒答。

    同时记录「低阈值直接拦截」的比例——这部分不消耗大模型调用。
    """
    from src import auth as AUTH
    from src.guard import LOW, check_scope

    client = None
    if use_guard:
        try:
            from src.extract import make_client

            client = make_client()
        except Exception:  # noqa: BLE001
            use_guard = False

    # 评测时强制打开护栏（不受管理端运行时开关影响），结束后还原
    prev_on = AUTH.get_setting("guard_on", "1")
    if client is not None:
        AUTH.set_setting("guard_on", "1")

    f = "买卖_二手车买卖合同_GF-2015-0120.docx"
    ok = direct = 0
    detail = []
    try:
        for q in out_of_scope:
            hits = cache[f]["bm25"].search(q, k=6)
            top = hits[0]["score"] if hits else 0.0
            is_direct = top < LOW
            direct += is_direct
            if use_guard and client is not None:
                passed, why = check_scope(q, hits, client)
                refused = not passed
            else:
                refused = is_direct
                why = "仅阈值判断"
            ok += refused
            detail.append({
                "question": q,
                "top_score": top,
                "direct_block": is_direct,
                "refused": refused,
                "why": why,
            })
    finally:
        AUTH.set_setting("guard_on", prev_on)

    return {
        "rate": round(ok / len(out_of_scope), 4),
        "direct_rate": round(direct / len(out_of_scope), 4),
        "guard_enabled_for_eval": client is not None,
        "detail": detail,
    }


def main() -> None:
    gold = load_gold()
    cases = gold["cases"]
    print(f"金标 {len(cases)} 条 / 库外 {len(gold['out_of_scope'])} 条")
    print("embedding:", "开启" if EMB.enabled() else "关闭（vector/hybrid 会退化）")

    t0 = time.time()
    cache = build_cache(cases)
    print(f"索引构建完成（{time.time() - t0:.1f}s，{len(cache)} 份合同）\n")

    strategies = ["bm25", "vector", "hybrid", "hybrid_rr"]
    results = {}
    print(f"{'策略':<14}{'Hit@1':>8}{'Hit@3':>8}{'Hit@5':>8}{'MRR@5':>8}")
    print("-" * 46)
    for s in strategies:
        r = evaluate(s, cases, cache)
        results[s] = r
        print(f"{s:<14}{r['hit@1']:>7.1%}{r['hit@3']:>8.1%}{r['hit@5']:>8.1%}{r['mrr@5']:>8.3f}")

    ref = refusal_rate(cache, gold["out_of_scope"])
    print(f"\n库外拒答率（护栏：阈值 + 意图分类）: {ref['rate']:.0%}  ({sum(d['refused'] for d in ref['detail'])}/{len(ref['detail'])})")

    # 每条策略漏掉了哪些
    for s in strategies:
        if results[s]["misses"]:
            print(f"\n{s} 漏检 {len(results[s]['misses'])} 条：")
            for m in results[s]["misses"][:5]:
                print("   -", m["question"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cases": len(cases),
                "strategies": results,
                "refusal": ref,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n结果已写入 {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
