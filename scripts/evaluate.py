"""评估脚本 v2：同时评估「条款抽取」和「风险判定」两层。

用法：python scripts/evaluate.py
结果写入 results/eval_v2.json（带版本号），并打印摘要。

两层指标：
1. 抽取层（把「present=true」当作正类）：accuracy / precision / recall / f1
2. 判定层：verdict（合规/偏离/缺失/冲突）与 severity（高/中/低）的命中率
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src.parser import parse
from src import extract as EX
from src.assess import assess


def compute_extraction_metrics(gold_items: list[dict], clauses: list[dict]) -> dict:
    """抽取层：present 判断的准确率 / 精确率 / 召回率 / F1。"""
    gold_present = {i["clause"]: bool(i["present"]) for i in gold_items}
    ext_present = {c["type"]: bool(c.get("present")) for c in clauses}

    tp = fp = fn = tn = 0
    for clause, g in gold_present.items():
        e = ext_present.get(clause, False)
        if g and e:
            tp += 1
        elif g and not e:
            fn += 1
        elif not g and e:
            fp += 1
        else:
            tn += 1

    total = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "accuracy_rate": round((tp + tn) / total, 4) if total else 0.0,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def compute_verdict_metrics(gold_items: list[dict], judgments: list[dict]) -> dict:
    """判定层：verdict 与 severity 的命中率。"""
    gold_verdict = {i["clause"]: i["verdict"] for i in gold_items}
    gold_sev = {i["clause"]: i["severity"] for i in gold_items}
    ext_verdict = {j["clause"]: j["verdict"] for j in judgments}
    ext_sev = {j["clause"]: j["severity"] for j in judgments}

    total = len(gold_verdict)
    verdict_ok = sum(1 for k in gold_verdict if gold_verdict[k] == ext_verdict.get(k))
    sev_ok = sum(1 for k in gold_sev if gold_sev[k] == ext_sev.get(k))
    return {
        "verdict_accuracy": round(verdict_ok / total, 4) if total else 0.0,
        "severity_accuracy": round(sev_ok / total, 4) if total else 0.0,
    }


def main() -> None:
    gold = json.loads((config.EVAL_DIR / "gold.json").read_text(encoding="utf-8"))
    client = EX.make_client()
    types = EX.load_clause_types()

    per_contract = []
    total_tokens = 0
    total_seconds = 0.0
    failed = []

    for c in gold["contracts"]:
        fname = c["file"]
        path = config.RAW_DIR / fname
        if not path.exists():
            failed.append(fname + "（文件不存在）")
            continue

        t0 = time.time()
        try:
            paragraphs = parse(path)
            clauses, usage = EX.extract(client, paragraphs, types)
            clauses = EX.validate(paragraphs, clauses)
            judgments = assess(clauses, types, paragraphs, client)
        except Exception as e:  # noqa: BLE001
            failed.append(f"{fname}: {str(e)[:80]}")
            continue
        dt = time.time() - t0

        ext_m = compute_extraction_metrics(c["items"], clauses)
        verdict_m = compute_verdict_metrics(c["items"], judgments)
        per_contract.append({
            "file": fname,
            **ext_m,
            **verdict_m,
            "tokens": usage["total_tokens"],
            "seconds": round(dt, 1),
        })

        total_tokens += usage["total_tokens"]
        total_seconds += dt
        print(f"  抽{ext_m['tp'] + ext_m['tn']}/13 判{int(verdict_m['verdict_accuracy'] * 13)}/13  {fname[:36]}")

    n = len(per_contract)
    if n == 0:
        print("没有可评估的合同，失败:", failed)
        return

    summary = {
        "version": 3,
        "contracts": n,
        "extraction": {
            "accuracy": round(sum(r["accuracy_rate"] for r in per_contract) / n, 4),
            "precision": round(sum(r["precision"] for r in per_contract) / n, 4),
            "recall": round(sum(r["recall"] for r in per_contract) / n, 4),
            "f1": round(sum(r["f1"] for r in per_contract) / n, 4),
        },
        "judgment": {
            "verdict_accuracy": round(sum(r["verdict_accuracy"] for r in per_contract) / n, 4),
            "severity_accuracy": round(sum(r["severity_accuracy"] for r in per_contract) / n, 4),
        },
        "total_tokens": total_tokens,
        "total_seconds": round(total_seconds, 1),
        "failed": failed,
    }

    config.RESULTS_DIR.mkdir(exist_ok=True)
    out_path = config.RESULTS_DIR / "eval_v3.json"
    out_path.write_text(
        json.dumps({"version": 3, "summary": summary, "per_contract": per_contract},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n===== 摘要 =====")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n结果已写入 {out_path}")


if __name__ == "__main__":
    main()
