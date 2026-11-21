"""交互式 demo：展示审查的完整过程（不只是最终答案）。

对应 Day14：demo 展示「过程」比展示「答案」更有说服力。
用法：python scripts/demo.py [合同文件名]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src.parser import parse, clause_headings
from src import extract as EX
from src.assess import assess
from src.report import generate_markdown


def demo(fname: str) -> None:
    client = EX.make_client()
    types = EX.load_clause_types()

    print(f"\n{'=' * 56}")
    print(f"审查合同：{fname}")
    print("=" * 56)

    # 1) 解析
    t0 = time.time()
    paragraphs = parse(config.RAW_DIR / fname)
    heads = clause_headings(paragraphs)
    print(f"\n[解析] {len(paragraphs)} 段，识别 {len(heads)} 个条款标题")
    for h in heads[:12]:
        print(f"   {h['clause_no']} {h['heading'][:26]}")

    # 2) 抽取
    clauses, usage = EX.extract(client, paragraphs, types)
    clauses = EX.validate(paragraphs, clauses)
    print("\n[抽取] 13 类条款：")
    for c in clauses:
        mark = "有" if c["present"] else "无"
        ev = (c["evidence"][:22] + "…") if c["evidence"] else ""
        print(f"   {mark}  {c['type']:<5} {ev}")

    # 3) 判定
    judgments = assess(clauses, types, paragraphs, client)
    high = [j for j in judgments if j["severity"] == "高"]
    mid = [j for j in judgments if j["severity"] == "中"]
    print(f"\n[判定] 高风险 {len(high)} · 中风险 {len(mid)} · 低风险 {len(judgments) - len(high) - len(mid)}")
    for j in high:
        print(f"   [高] {j['clause']}：{j['verdict']}")

    # 4) 报告 + 成本
    dt = time.time() - t0
    report = generate_markdown(fname, judgments, types, usage=usage, seconds=dt)
    print(f"\n[报告]\n{report}")
    print(f"\n[成本] {dt:.1f} 秒 · {usage['total_tokens']} tokens")


if __name__ == "__main__":
    default = "买卖_家具买卖合同_GF-2000-0105.docx"
    fname = sys.argv[1] if len(sys.argv) > 1 else default
    demo(fname)
