# 设计文档：合同审查 Agent

## 一、架构与数据流

```
上传合同 (.docx)
   ↓
parser     解析：段落 + 条款号 + 标题（表格也解析，合并单元格去重）
   ↓
extract    LLM 抽取 13 类条款（present + 原文引用 evidence + confidence）
            → 后置校验：evidence 必须原文可搜，搜不到置信度归零
   ↓
assess     风险判定：规则层（缺失/偏离）+ LLM 语义层（合规/冲突），severity 按 playbook
   ↓
confirm    【人工确认】高风险条款用 interrupt 暂停，人 approve/edit 后 resume
   ↓
report     生成 Markdown 审查报告（风险清单 + 原文定位 + 参考建议 + 免责声明）
```

另有一条旁支（AI 对话）：

```
用户提问 → 护栏（阈值 + 意图分类，越界直接拒答）
         → 混合检索（BM25 + 向量 → RRF 融合 → Rerank 精排）
         → LLM 只基于原文回答 + 引用条款号
         → 需要算数/查法条/取条款原文时，调工具（function calling）
```

## 二、手写流程 vs LangGraph 图版

| 维度 | 手写顺序脚本 | LangGraph 状态图 |
|---|---|---|
| 结构 | `report = report(assess(extract(parse(f))))` 一串函数 | 显式节点 + 边，state 统一传递 |
| 加一步 | 改函数签名、层层传参 | `add_node` + `add_edge`，不动现有节点 |
| 人工确认 | 要自己写暂停/恢复逻辑、自己存状态 | `interrupt()` + `Command(resume=...)` 原生支持 |
| 断点续跑 | 自己序列化中间状态 | `checkpointer` 自动持久化，任意节点可恢复 |
| 可观测 | 手动打印 | 每个节点可插日志/追踪 |
| 适用 | 线性流程、无人工介入 | **有分支/人工确认/需要恢复的流程** |

**结论**：核心逻辑（parse/extract/assess/revision/report）完全复用，LangGraph 只负责**编排**。
现在**主链路就是这张图**：`/api/review` 以 `auto_confirm=true` 走快速模式，
`/api/review_graph` 走人工确认模式（interrupt + resume），两条入口共用同一批节点、输出结构一致。

## 三、关键设计决策

1. **评估先于优化**：`data/eval/gold.json`（403 条）在写任何算法前先建好，所有数字都从它来。
2. **抽取的「原文可搜」校验**：模型必须输出原文引用，子串搜不到就置信度归零——这是防幻觉的第一道闸。
3. **风险判定分层**：规则层（缺失/偏离）先跑、可解释、零成本；LLM 语义层（合规/冲突）在条款有正文时启用，判断"违约金超标"这类语义风险。
4. **playbook 是唯一评分依据**：13 类条款的 `must_contain` / `red_flags` 决定一切判定，且每条可追溯到合同范本。
5. **版本化结果**：每次评估写 `results/eval_vN.json`，消融实验靠它对比。
6. **问答复用同一套检索**：AI 对话复用 `retrieve.py`，保证"回答有出处"。
7. **检索用数据选型**：30 条检索金标做 4 策略消融（纯 BM25 / 纯向量 / 混合 / 混合+Rerank），
   Hit@3 由 63.3% → 80.0%，Hit@1 63.3%；据此定为默认链路，且未配 embedding 时自动退回 BM25。
8. **算数不交给模型**：违约金/逾期利息由 `calc_penalty` 工具用代码算，模型只负责组织语言。

## 四、已知局限（诚实记录）

- 数据以**空白示范文本**为主（仅 2 份填充示例），暂无大量真实「合规/冲突」样本；
- 判定层的 verdict 准确率（91.07%）受 gold 粗糙度影响，需人工精标才能公平衡量；
- 检索向量化依赖外部 embedding API（硅基流动），未配则退回纯 BM25；
- LangGraph 状态存在内存（`MemorySaver`），服务重启后待确认任务会失效；
- DOCX 页码是估算（靠显式分页符），不是精确页码。
