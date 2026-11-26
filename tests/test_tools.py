"""问答工具集（纯函数，不调用大模型）。"""

from pathlib import Path

from src.parser import parse
from src.tools import TOOLS, build_executor

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "raw" / "示例_填写版_家具买卖合同_冲突.docx"


def test_tool_definitions():
    names = {t["function"]["name"] for t in TOOLS}
    assert names == {"get_clause", "search_law", "calc_penalty", "get_review_summary"}
    for t in TOOLS:
        assert t["type"] == "function"
        assert t["function"]["description"]


def test_calc_penalty_by_percent():
    ex = build_executor([], "")
    out = ex("calc_penalty", {"amount": 1_000_000, "rate_percent": 20})
    assert "200,000.00" in out


def test_calc_penalty_by_days():
    ex = build_executor([], "")
    out = ex("calc_penalty", {"amount": 1_000_000, "daily_rate": 5, "days": 30})
    assert "15,000.00" in out


def test_calc_penalty_requires_params():
    ex = build_executor([], "")
    out = ex("calc_penalty", {"amount": 100})
    assert "需要提供" in out


def test_calc_penalty_bad_amount():
    ex = build_executor([], "")
    assert "金额" in ex("calc_penalty", {"amount": -5})


def test_get_clause_found():
    paras = parse(SAMPLE)
    ex = build_executor(paras, "")
    out = ex("get_clause", {"clause_name": "违约责任"})
    assert "违约" in out


def test_get_clause_not_found():
    paras = parse(SAMPLE)
    ex = build_executor(paras, "")
    out = ex("get_clause", {"clause_name": "星舰发射"})
    assert "没有找到" in out


def test_search_law_hits_article():
    ex = build_executor([], "")
    out = ex("search_law", {"keyword": "违约金 上限"})
    assert "第五百八十五条" in out


def test_review_summary_tool():
    ex = build_executor([], "高风险 2 条")
    assert ex("get_review_summary", {}) == "高风险 2 条"
    ex2 = build_executor([], "")
    assert "还没有审查记录" in ex2("get_review_summary", {})


def test_unknown_tool_returns_message():
    ex = build_executor([], "")
    assert "未知工具" in ex("nope", {})
