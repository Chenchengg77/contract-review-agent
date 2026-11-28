"""判定依据：playbook 规则 → 三层依据（纯代码，不调模型）。"""

import json
from pathlib import Path

from src import report_agent

ROOT = Path(__file__).resolve().parent.parent


def _types() -> list[dict]:
    data = json.loads((ROOT / "data" / "playbook" / "clauses.json").read_text(encoding="utf-8"))
    return data["clause_types"]


def test_basis_attached_for_non_compliant():
    types = _types()
    judgments = [
        {"clause": "违约金", "verdict": "冲突", "severity": "高", "reason": "超上限"},
        {"clause": "付款条款", "verdict": "合规", "severity": "低", "reason": "符合"},
    ]
    n = report_agent.build_basis(judgments, types)
    assert n == 1
    assert "basis" in judgments[0]
    assert "basis" not in judgments[1], "合规条款不需要判定依据"
    basis = judgments[0]["basis"]
    assert basis["must_contain"] and basis["red_flags"] and basis["standard_text"]
    assert basis["legal_ref"]["article"] == "第五百八十五条"


def test_basis_covers_all_13_types():
    types = _types()
    judgments = [{"clause": t["name"], "verdict": "偏离", "severity": "中"} for t in types]
    n = report_agent.build_basis(judgments, types)
    assert n == len(types) == 13
    for j in judgments:
        assert j["basis"]["must_contain"], f"{j['clause']} 缺必备要素"
        assert j["basis"]["red_flags"], f"{j['clause']} 缺红线"


def test_law_ref_only_for_mapped_clauses():
    assert report_agent.law_ref("违约金")["article"] == "第五百八十五条"
    assert report_agent.law_ref("不可抗力")["article"] == "第五百九十条"
    # 库里没有可靠对应的条款：不给法条（宁缺勿错）
    assert report_agent.law_ref("保密条款") is None
    assert report_agent.law_ref("知识产权") is None
    assert report_agent.law_ref("不存在的条款") is None
