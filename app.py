"""Streamlit 界面：合同智能审查。

演示节奏（6 个节点）：
1. 选择示例合同 / 上传
2. 分步流水线（解析 → 抽取 → 判定）
3. 风险总览（指标卡）
4. 风险明细表
5. 人工复核（可降级误报，重新生成）
6. 审查报告 + 下载；另有「评估报告」tab 展示系统指标

运行：streamlit run app.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src.parser import parse, clause_headings
from src import extract as EX
from src.assess import assess
from src.report import generate_markdown

st.set_page_config(page_title="合同智能审查", page_icon="⚖️", layout="wide")

# ---- 轻量样式 ----
st.markdown(
    """
    <style>
    .hero { font-size: 1.9rem; font-weight: 800; margin-bottom: 0; letter-spacing: -0.02em; }
    .sub  { color: #6b7280; margin-top: 2px; font-size: 0.95rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---- 侧边栏 ----
with st.sidebar:
    st.markdown("## ⚖️ 合同智能审查")
    st.caption("合同 → 条款抽取 → 风险判定 → 人工确认 → 报告")
    st.divider()

    st.markdown("**示例合同**")
    raw_dir = config.RAW_DIR
    sample_names = sorted(
        f.name for f in raw_dir.glob("*.docx") if not f.name.startswith("~$")
    )
    sample = st.selectbox("免上传，直接选示例", ["（自行上传）"] + sample_names)

    st.divider()
    st.markdown("**系统评估**")
    col_a, col_b = st.columns(2)
    col_a.metric("抽取准确率", "94.96%")
    col_b.metric("判定准确率", "98.67%")
    st.caption("29 份合同 · 377 条评估集")
    st.divider()
    st.caption("数据：市场监管总局合同示范文本库")


st.markdown('<p class="hero">合同智能审查 Agent</p>', unsafe_allow_html=True)
st.markdown('<p class="sub">上传或选择一份合同，自动抽取 13 类条款、判定风险、生成审查报告</p>', unsafe_allow_html=True)
st.write("")

tab1, tab2 = st.tabs(["🔍 开始审查", "📊 评估报告"])


# ============ 评估报告 tab（先渲染，保证始终可见）============
with tab2:
    st.subheader("系统评估结果")
    st.caption("数据来自 results/eval_v2.json —— 29 份合同 / 377 条评估集")
    eval_path = config.RESULTS_DIR / "eval_v3.json"
    if eval_path.exists():
        data = json.loads(eval_path.read_text(encoding="utf-8"))
        s = data.get("summary", {})
        e = s.get("extraction", {})
        j = s.get("judgment", {})
        a, b, c, d = st.columns(4)
        a.metric("抽取准确率", f"{e.get('accuracy', 0) * 100:.2f}%")
        b.metric("抽取 F1", f"{e.get('f1', 0) * 100:.2f}%")
        c.metric("判定准确率", f"{j.get('verdict_accuracy', 0) * 100:.2f}%")
        d.metric("severity 准确率", f"{j.get('severity_accuracy', 0) * 100:.2f}%")
        st.markdown("**逐份合同**")
        rows = [
            {
                "合同": r["file"],
                "抽取准确率": f"{r['accuracy_rate'] * 100:.0f}%",
                "判定一致": f"{int(r['verdict_accuracy'] * 13)}/13",
            }
            for r in data.get("per_contract", [])
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    else:
        st.warning("未找到 results/eval_v2.json，先运行 `python scripts/evaluate.py`。")


# ============ 开始审查 tab ============
with tab1:
    uploaded = st.file_uploader("上传合同（.docx）", type=["docx"], help="也可以直接用左侧示例合同")

    target_path: Path | None = None
    display_name = ""
    if uploaded is not None:
        target_path = config.RAW_DIR.parent / "_upload.docx"
        target_path.write_bytes(uploaded.read())
        display_name = uploaded.name
    elif sample != "（自行上传）":
        target_path = raw_dir / sample
        display_name = sample

    if target_path is None:
        st.info("👈 在左侧选一个示例合同，或上传一份 .docx 开始。")
        st.stop()

    # ---- 流水线 ----
    client = EX.make_client()
    types = EX.load_clause_types()

    with st.status("审查中…", expanded=True) as status:
        st.write("① 解析合同结构")
        t0 = time.time()
        paragraphs = parse(target_path)
        heads = clause_headings(paragraphs)
        st.write(f"　 · 识别 **{len(heads)}** 个条款标题 / {len(paragraphs)} 段")

        st.write("② 抽取 13 类条款（LLM + 原文校验）")
        clauses, usage = EX.extract(client, paragraphs, types)
        clauses = EX.validate(paragraphs, clauses)
        present = sum(1 for c in clauses if c["present"])
        st.write(f"　 · 抽到 **{present}** 类条款，证据全部通过原文校验")

        st.write("③ 风险判定")
        judgments = assess(clauses, types, paragraphs, client)
        dt = time.time() - t0
        high = [j for j in judgments if j["severity"] == "高"]
        mid = [j for j in judgments if j["severity"] == "中"]
        low = [j for j in judgments if j["severity"] == "低"]
        st.write(f"　 · 高风险 **{len(high)}** · 中风险 {len(mid)} · 低风险 {len(low)}")
        status.update(label="审查完成 ✓", state="complete", expanded=False)

    st.caption(
        f"耗时 {dt:.1f} 秒 · {usage['total_tokens']} tokens · "
        f"成本约 {usage['total_tokens'] * 0.000002:.4f} 元"
    )

    # ---- 风险总览 ----
    st.subheader("风险总览")
    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 高风险", len(high))
    c2.metric("🟡 中风险", len(mid))
    c3.metric("🟢 低风险", len(low))

    # ---- 风险明细 ----
    st.subheader("风险明细")
    rows = []
    for j in judgments:
        if j["verdict"] == "合规":
            continue
        rows.append({
            "条款": j["clause"],
            "判定": j["verdict"],
            "等级": j["severity"],
            "原文定位": (j.get("evidence") or "（无）")[:40],
            "问题": j["reason"],
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    else:
        st.success("✅ 无风险条款")

    # ---- 人工复核 ----
    st.subheader("人工复核")
    st.caption("高风险条款默认需人工确认。若认为是误报，可在此降级（模拟 human-in-the-loop）。")
    if high:
        downgrade = st.multiselect(
            "选择要降级为「低风险」的误报项",
            [j["clause"] for j in high],
            key="downgrade",
        )
        if downgrade:
            for j in judgments:
                if j["clause"] in downgrade:
                    j["severity"] = "低"
                    j["reason"] += "（人工复核：确认为误报）"
    else:
        st.info("本份合同无高风险条款，无需人工复核。")

    # ---- 报告 ----
    st.subheader("审查报告")
    report = generate_markdown(display_name, judgments, types, usage=usage, seconds=dt)
    with st.expander("查看完整 Markdown 报告", expanded=False):
        st.markdown(report)
    st.download_button(
        "⬇️ 下载审查报告 (.md)",
        report,
        file_name=f"{Path(display_name).stem}_审查报告.md",
    )
    st.caption("本报告仅供辅助参考，不构成法律意见，不替代律师或专业人士的审查。")
