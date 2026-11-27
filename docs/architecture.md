# 架构与关键设计

本文说明系统分层、审查流水线、护栏决策、对比流程、数据模型，以及几处「为什么这么设计」的取舍。

---

## 1. 系统分层

```mermaid
flowchart TB
    subgraph FE["前端（Vue 3 SPA）"]
        U1["用户端<br/>首页 / 审查 / 对话 / 对比 / 模板 / 评估"]
        U2["个人中心<br/>概览 / 我的审查 / 报告详情 / 账户"]
        U3["管理端<br/>看板 / 用户 / 记录 / 运维"]
    end

    subgraph BE["后端（FastAPI）"]
        A1["认证与权限<br/>session token + role"]
        A2["审查接口 /api/review"]
        A3["问答接口 /api/chat(_stream)"]
        A4["对比接口 /api/compare_upload"]
        A5["管理接口 /api/admin/*"]
    end

    subgraph CORE["业务核心（src/）"]
        P["parser<br/>DOCX 解析 + 条款号"]
        EX["extract<br/>LLM 抽取 13 类条款"]
        AS["assess<br/>规则 + 语义判定"]
        RV["revision<br/>修订建议生成"]
        RT["retrieve<br/>BM25 检索"]
        QA["qa / law_qa<br/>RAG 问答"]
        GD["guard<br/>前置护栏"]
    end

    DB[("SQLite<br/>users / sessions / reviews / settings")]
    LLM["DeepSeek API"]
    FS[("data/raw<br/>合同与模板")]

    FE --> BE
    A2 --> P --> EX --> AS --> RV
    A3 --> GD --> RT --> QA
    A4 --> P
    A1 --> DB
    A2 --> DB
    A5 --> DB
    EX --> LLM
    AS --> LLM
    RV --> LLM
    QA --> LLM
    P --> FS
```

---

## 2. 审查流水线

```mermaid
sequenceDiagram
    participant U as 用户
    participant API as FastAPI
    participant P as parser
    participant E as extract
    participant A as assess
    participant R as revision
    participant DB as SQLite

    U->>API: POST /api/review (file / sample)
    API->>P: 解析 DOCX（段落 + 表格 + 条款号）
    P-->>API: blocks[]
    API->>E: 抽取 13 类条款（LLM）
    E-->>API: clauses[]（含 evidence / clause_no）
    API->>A: 风险判定（规则层 + 语义层）
    A-->>API: judgments[]（verdict / severity / reason）
    API->>R: 对「偏离 / 冲突」生成修订建议
    R-->>API: revision 文本
    API->>DB: 写入 review（高/中/低 + judgments + duration）
    API-->>U: 审查报告（可复制修订建议）
```

**关键点**

| 环节 | 设计 | 为什么 |
|---|---|---|
| 解析 | 保留段落与表格结构，识别 `第X条` | 条款判定要能引用原文位置 |
| 抽取 | 要求 `evidence` 必须在原文中可搜到 | 防模型编造条款 |
| 判定 | 规则层（playbook 关键要素）+ 语义层 | 规则稳定、语义覆盖边界情况 |
| 修订 | 只对「偏离/冲突」生成 | 省钱，也避免无意义的改写 |
| 落库 | 存 `judgments` JSON | 报告详情、对话上下文都要用 |

---

## 3. 前置护栏（Guardrails）

```mermaid
flowchart LR
    Q["用户问题"] --> R["BM25 检索"]
    R --> S{"最高分"}
    S -- "低于阈值 low" --> REJ["直接拒答<br/>（不调模型）"]
    S -- "高于阈值 high" --> PASS["放行<br/>直接回答"]
    S -- "灰区" --> CLS["意图分类（1 次小调用）"]
    CLS -- "范围内" --> PASS
    CLS -- "越界" --> REJ
```

- 阈值可在**管理端 → 系统运维**运行时调整（默认 5.0 / 8.0），改完立即生效
- 越界直接拒答，**不消耗大模型调用**
- 关闭开关可对比「有/无护栏」的差异（演示用）

---

## 4. 合同对比

```mermaid
flowchart LR
    A["A 合同（样例/上传）"] --> X["抽取 13 类条款"]
    B["B 合同（样例/上传）"] --> X
    X --> C["逐条比对<br/>归一化后比较文本"]
    C --> D["分类：新增 / 删除 / 修改 / 相同"]
    D --> E["风险等级<br/>优先用 B 的最近审查结论<br/>否则规则推断"]
    E --> F["Diff 视图 / 统计看板 / 风险摘要"]
```

**风险等级的来源是分层的**：B 合同若做过审查，用审查判定的 severity；没有则按规则推断（删除=高 / 修改=中 / 新增=低），并在界面上标注「规则推断」。

---

## 5. 数据模型

```mermaid
erDiagram
    users ||--o{ sessions : "持有"
    users ||--o{ reviews : "产生"

    users {
        int id PK
        string username UK
        string password_hash
        string role "user / admin"
        real created_at
        string default_contract_type
        string default_focus
        string perspective
        real last_login
        string user_status "active / disabled"
        string security_question
        string security_answer_hash
    }
    sessions {
        string token PK
        int user_id FK
        real expires_at
    }
    reviews {
        int id PK
        int user_id FK
        string filename
        int high
        int mid
        int low
        real created_at
        text judgments "JSON"
        string status "ok / failed / retried"
        text error
        real duration
    }
    settings {
        string key PK
        string value
    }
```

- **轻量迁移**：启动时用 `PRAGMA table_info` 检查缺列并 `ALTER TABLE ADD COLUMN`，老库可直接升级
- `settings` 存运行时配置（护栏开关、阈值、审查超时），管理员改完即生效

---

## 6. LangGraph 编排与人工确认

审查流水线除了顺序函数版本，还提供一条 **LangGraph 状态图**路径（`src/workflow.py`）：

```mermaid
flowchart LR
    S([START]) --> P["parse"]
    P --> E["extract<br/>抽取 13 类条款"]
    E --> A["assess<br/>规则 + 语义判定"]
    A --> RV["revise<br/>修订建议"]
    RV --> C{"confirm<br/>存在高风险?"}
    C -- "否 / 快速模式" --> R["report"]
    C -- "是 & 人工确认" --> I["interrupt<br/>暂停，返回 pending"]
    I -- "Command(resume)" --> R
    R --> EN([END])
```

**一张图，两条入口**（主链路就是它，不是"附加实现"）：

| 入口 | 模式 | 说明 |
|---|---|---|
| `POST /api/review` | 快速 | 传 `auto_confirm=true`，审查一口气跑完，行为与旧版一致 |
| `POST /api/review_graph` | 人工确认 | 有高风险时 `interrupt` 暂停，返回 `pending` + `thread_id` |
| `POST /api/review_graph/resume` | — | 传 `thread_id` + `action`（`approve`/`edit`）+ 可选 `changes` |

两条路径共用同一批节点，输出结构一致：`process`（段落数/条款数/耗时/tokens）、`overview`（高/中/低）、`judgments`（含 `revision`）。

**为什么需要它**

| 场景 | 顺序函数 | LangGraph |
|---|---|---|
| 高风险直接出报告 | 可以 | 可暂停等人确认 |
| 人确认后继续 | 只能整条重跑（重复耗 LLM） | `Command(resume)` **从断点继续** |
| 人修改判定 | 不支持 | 可用 `changes` 覆盖某条 verdict/severity 后再生成报告 |
| 多轮/长流程扩展 | 需要自己写状态机 | 加节点即可 |

**接口**

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/review_graph` | 启动；支持示例合同（`name`）或上传（`file`）；有高风险返回 `status=pending` + `thread_id` + 高风险清单 |
| POST | `/api/review_graph/resume` | 传 `thread_id` + `action`（`approve`/`edit`）+ 可选 `changes`，恢复执行 |

**两个实现细节（踩过坑）**

1. **`Command(resume={})` 传空字典会被当成"没有恢复值"**，图会一直卡在 interrupt。所以确认参数统一成结构化对象 `{action, changes}`，永远非空。
2. **状态存在 checkpointer 里**（当前 `MemorySaver`，进程内内存）：
   - 服务重启 / Render 休眠唤醒后，待确认任务会失效（点确认返回 404）
   - 多 worker 部署时，请求可能打到没有该状态的进程
   - 上生产应换 `SqliteSaver` / `PostgresSaver` 落库

---

## 7. 错误处理策略

| 场景 | 处理 |
|---|---|
| 文件解析失败 | 记录 `status=failed` + 错误信息，管理端可**重试** |
| 大模型超时 | 同上；超时时间可在运维页调整（演示可改成 0.5s 制造真实故障） |
| 问答检索不到 | **直接拒答**，不猜 |
| 分析中异常 | 前端提示，不写坏数据 |
| 账号被禁用 | 登录返回 403，并清空其全部会话 |

---

## 8. 几处取舍（面试常被问）

1. **为什么不直接用大模型聊天审合同？**
   → 聊天模型会编、无定位、不可评测。所以做成「抽取 → 判定 → 修订」的流水线，每步可验证。

2. **为什么用 BM25 而不是纯向量？**
   → 合同问答里条款名、数字是强关键词，BM25 对「第X条」「30%」这类精确匹配更稳，也省掉了 embedding 服务依赖。

3. **为什么 SQLite？**
   → 单实例演示足够，零运维；上生产会换 PostgreSQL，代码层只需替换数据访问实现。

4. **为什么审核是同步请求？**
   → 单份约 16 秒，同步实现简单、前端可显示阶段进度；上生产会改任务队列（异步 + 轮询/SSE）。

5. **评测数字怎么来的？**
   → 31 份合同 / 403 条人工金标，脚本 `scripts/evaluate.py` 可复跑；每次改动用例都有前后对比（见 `docs/failures.md`）。
