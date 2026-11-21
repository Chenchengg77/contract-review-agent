"""单份合同审查：parse -> extract -> assess -> 生成报告。

用法：python scripts/review.py [合同文件名]
不带参数时默认审查家具买卖合同；报告写入 results/ 目录。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src.parser import parse
from src import extract as EX
from src.assess import assess
from src.report import generate_markdown


def review(fname: str) -> str:
    path = config.RAW_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"找不到合同：{path}")

    client = EX.make_client()
    types = EX.load_clause_types()

    paragraphs = parse(path)
    t0 = time.time()
    clauses, usage = EX.extract(client, paragraphs, types)
    clauses = EX.validate(paragraphs, clauses)
    judgments = assess(clauses, types, paragraphs, client)
    dt = time.time() - t0

    report = generate_markdown(fname, judgments, types, usage=usage, seconds=dt)

    config.RESULTS_DIR.mkdir(exist_ok=True)
    out_path = config.RESULTS_DIR / (Path(fname).stem + "_report.md")
    out_path.write_text(report, encoding="utf-8")
    print(f"报告已写入 {out_path}\n")
    return report


if __name__ == "__main__":
    default = "买卖_家具买卖合同_GF-2000-0105.docx"
    fname = sys.argv[1] if len(sys.argv) > 1 else default
    print(review(fname))
