"""审查报告生成：把判定结果组织成 Markdown 报告。

输出结构：
1. 风险总览（高/中/低计数）
2. 风险明细（每条：条款、原文定位、判定、理由、参考建议）
3. 待人工复核清单（高风险条款，触发 Step 15 的人工确认）
4. 成本/耗时 + 免责声明
"""

from __future__ import annotations

from datetime import datetime

_SEVERITY_ORDER = ["高", "中", "低"]


def _counts(judgments: list[dict]) -> dict[str, int]:
    c = {"高": 0, "中": 0, "低": 0}
    for j in judgments:
        c[j.get("severity", "低")] = c.get(j.get("severity", "低"), 0) + 1
    return c


def _group_by_severity(judgments: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {"高": [], "中": [], "低": []}
    for j in judgments:
        # 合规（低风险）不写进风险明细，只统计
        if j["verdict"] == "合规":
            continue
        grouped.setdefault(j.get("severity", "中"), []).append(j)
    return grouped


def generate_markdown(
    filename: str,
    judgments: list[dict],
    clause_types: list[dict],
    usage: dict | None = None,
    seconds: float | None = None,
) -> str:
    """生成 Markdown 审查报告。judgments 为 assess() 的输出。"""
    playbook = {t["name"]: t for t in clause_types}
    counts = _counts(judgments)
    grouped = _group_by_severity(judgments)

    lines: list[str] = []
    lines.append("# 合同审查报告\n")
    lines.append(f"**合同文件**：{filename}  ")
    lines.append(f"**审查时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1) 风险总览
    lines.append("## 一、风险总览\n")
    lines.append("| 风险等级 | 数量 |")
    lines.append("|---|---|")
    for sev in _SEVERITY_ORDER:
        lines.append(f"| {sev}风险 | {counts.get(sev, 0)} |")
    lines.append("")

    # 2) 风险明细
    lines.append("## 二、风险明细\n")
    for sev in _SEVERITY_ORDER:
        items = grouped.get(sev, [])
        if not items:
            continue
        lines.append(f"### {sev}风险（{len(items)} 项）\n")
        for j in items:
            entry = playbook.get(j["clause"], {})
            evidence = j.get("evidence") or "（无原文定位）"
            lines.append(f"#### {j['clause']} —— {j['verdict']}")
            lines.append(f"- **问题**：{j['reason']}")
            lines.append(f"- **原文定位**：{evidence}")
            if j["verdict"] in ("偏离", "缺失", "冲突") and entry.get("standard_text"):
                lines.append(f"- **参考建议**：{entry['standard_text']}")
            lines.append("")

    # 3) 待人工复核
    review = [j for j in judgments if j.get("severity") == "高"]
    lines.append("## 三、待人工复核\n")
    if review:
        lines.append(f"以下 **{len(review)} 项高风险条款**需人工确认后才能进入最终报告：\n")
        for j in review:
            lines.append(f"- {j['clause']}：{j['reason']}")
    else:
        lines.append("无高风险条款。\n")

    # 4) 成本 + 免责
    lines.append("## 四、审查信息与声明\n")
    meta = []
    if seconds is not None:
        meta.append(f"耗时 {seconds:.1f} 秒")
    if usage:
        meta.append(f"{usage.get('total_tokens', 0)} tokens")
    if meta:
        lines.append(" · ".join(meta) + "\n")
    lines.append("> 本报告由合同审查系统自动生成，仅作辅助参考，不构成法律意见，不替代律师或专业人士的审查。")

    return "\n".join(lines)
