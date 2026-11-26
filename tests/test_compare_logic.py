"""合同对比的纯逻辑（不依赖大模型）。"""

from api import _compare, _enrich_diffs


def _clause(present: bool, text: str = "") -> dict:
    return {"present": present, "evidence": text[:20], "text": text}


def _sample():
    return {
        "付款条款": _clause(True, "甲方应在收货后 30 日内付款"),
        "违约金": _clause(True, "违约金为合同总额的 20%"),
        "保密条款": _clause(False),
        "知识产权": _clause(True, "知识产权归甲方所有"),
    }


def test_compare_counts_all_four_kinds():
    a = _sample()
    b = _sample()
    # 修改：付款条款
    b["付款条款"] = _clause(True, "甲方应在收货后 60 日内付款")
    # 删除：违约金
    b["违约金"] = _clause(False)
    # 新增：保密条款
    b["保密条款"] = _clause(True, "双方对保密信息承担保密义务")
    # 相同：知识产权

    result = _compare(a, b)
    s = result["summary"]
    assert s["修改"] == 1
    assert s["删除"] == 1
    assert s["新增"] == 1
    assert s["相同"] == 1
    assert len(result["diffs"]) == 4


def test_compare_identical_contracts():
    result = _compare(_sample(), _sample())
    assert result["summary"]["修改"] == 0
    assert result["summary"]["新增"] == 0
    assert result["summary"]["删除"] == 0
    assert result["summary"]["相同"] == 4


def test_compare_marks_change_type_per_clause():
    a = _sample()
    b = _sample()
    b["违约金"] = _clause(False)
    result = _compare(a, b)
    item = next(d for d in result["diffs"] if d["clause"] == "违约金")
    assert item["change"] == "删除"
    assert item["b_text"] == "（无此类条款）"


def test_enrich_diffs_sets_severity_by_rule():
    a = _sample()
    b = _sample()
    b["付款条款"] = _clause(True, "甲方应在收货后 60 日内付款")  # 修改
    b["违约金"] = _clause(False)  # 删除
    b["保密条款"] = _clause(True, "新增保密义务")  # 新增

    result = _enrich_diffs(_compare(a, b), b_name="")
    by = {d["clause"]: d for d in result["diffs"]}

    assert by["违约金"]["severity"] == "高"
    assert by["付款条款"]["severity"] == "中"
    assert by["保密条款"]["severity"] == "低"
    # 没有审查数据时标注来源为规则推断
    assert by["违约金"]["severity_from"] == "rule"
    # 相同条款不带风险与说明
    assert by["知识产权"]["severity"] == ""
    assert by["知识产权"]["note"] == ""
    # 每条差异都有说明文字
    assert by["违约金"]["note"]
