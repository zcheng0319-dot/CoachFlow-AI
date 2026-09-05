# CoachFlow AI：从招生咨询到双端 Agent 转化闭环

## 一句话定位

面向少儿运动培训机构的 AI-native lead conversion system：用共享业务数据同时服务家长咨询与机构内部转化。

## 问题定义

少儿培训的招生流程不是一个独立的咨询窗口，而是一条持续变化的链路：

```text
Lead → 课程匹配 → 试听 → 转化判断 → 跟进
```

经营者需要回答的问题通常跨越多个系统事实：某位家长是否值得优先联系、孩子适合哪个仍有名额的班、试听后迟迟未报名的原因、最新沟通是否应该进入 CRM。传统 CRM 要求员工在多个界面之间查找、录入和判断，信息容易滞后或丢失。

CoachFlow 的产品假设是：家长与员工需要不同的 AI 体验，但可以共享同一套知识、课程与 CRM 业务层。家长获得课程咨询，员工获得线索分析和受控操作。

## 双端产品模型

| Experience | 用户 | 核心问题 | 架构 |
| --- | --- | --- | --- |
| CoachFlow Copilot | 老板、店长、招生顾问、课程顾问 | 今天应该关注哪个客户，下一步做什么？ | Multi-Agent |
| CoachFlow Concierge | 潜在家长、潜在学员 | 我的孩子适合学什么，下一步如何开始？ | Single Agent |

Copilot 处理 CRM、Lead、课程、试听、Interaction、评分、转化和跟进；Concierge 当前只处理训练咨询、水平判断、课程匹配和课程信息确认。二者共享 Volcano Engine Knowledge Base、FastAPI Structured Tools 和 SQLite prototype，但 Tool 权限按 Persona 分配。

## 用户与场景

| 角色 | 需要完成的任务 | 当前摩擦 |
| --- | --- | --- |
| 店长 / 运营 | 判断今天优先跟进谁 | 试听、互动、状态分散，优先级依赖经验 |
| 课程顾问 | 为孩子匹配可报名班级 | 年龄、水平、时间、预算、容量要同时考虑 |
| 招生顾问 | 记录新咨询和新反馈 | 手工录入负担高，聊天噪声会污染 CRM |
| 潜在家长 / 学员 | 判断孩子适合什么、如何开始 | 通用训练知识与当前课程信息分散，难以完成下一步 |

当前用少儿乒乓球培训验证该链路；相同模式可以迁移到篮球、羽毛球、网球等存在“咨询—课程—试听—转化”流程的培训业务。

## Why Agent

这个场景需要连续决策，而不是一次性检索。以“张女士试听满意但觉得贵，还值得跟吗？”为例：

1. 定位客户；
2. 获取 Lead、试听和互动历史；
3. 基于事实提取信号；
4. 调用确定性 Lead Score；
5. 必要时查询可替代课程；
6. 输出下一步建议，而不是假称已经执行。

上述复杂链路属于 Staff Copilot，因此由主控 Agent 识别任务并分发给线索、课程和转化 Agent。Customer Concierge 的任务空间较窄，使用 Single Agent，减少路由错误、token 成本、延迟和上下文交接。架构跟随任务复杂度，而不是把 Multi-Agent 本身当作产品卖点。

## 核心产品决策

### 决策 1：将 RAG 与实时业务事实分开

Volcano Engine Knowledge Base / RAG 已在 Coze Agent 中用于水平判断、训练原则、试听 FAQ 和稳定业务知识。班级名额、价格、教练、CRM 互动和试听记录会变化，必须来自结构化 Tool。这样避免模型把历史知识当作当前业务事实。

### 决策 2：把 LLM 放在解释层，而不是事实层

LLM 可以理解自然语言、路由任务、归纳证据并生成建议。FastAPI + SQLite 则负责参数校验、事实查询、写入、推荐排序和评分。模型不直接拥有“客户事实”的最终解释权。

### 决策 3：为写操作设置权限边界

`create_followup` 是需要人工确认的 L2 操作；报名、支付、退款、删除等 L3 操作不在 V1 开放范围。`upsert_lead` 与 `record_interaction` 只保存明确传入的事实，不自动推断意向、预算标签或客户状态。

### 决策 4：把 CRM 写回做成数据质量问题

`record_interaction` 会规范化文本，拒绝低信息内容，并在同 Lead、同渠道的 10 分钟窗口内拦截完全重复和高相似重复。近重复规则使用 `SequenceMatcher`，阈值 0.90；它只控制明显的重复事实，不做“价格敏感”或“高意向”之类的语义推理。

### 决策 5：先验证闭环，不先建设完整 SaaS

V1 聚焦高频链路中的读、写、分析和跟进边界。完整后台、支付、真实消息渠道、生产身份系统和分布式基础设施都不进入当前范围，避免用功能数量掩盖核心假设尚未验证的问题。

### 决策 6：按 Persona 分配能力

Staff Copilot 可以访问 CRM、Lead Score、互动与跟进能力；Customer Concierge 只访问知识库、`get_course_info` 和 `recommend_courses`。家长端不访问其他客户信息、内部销售标签、员工跟进策略或销售优先级；`upsert_lead` 仅作为未来受控 Lead Capture 方向。

## 已实现的能力

- FastAPI + SQLite 业务后端和 OpenAPI Tool 契约。
- Lead、试听、互动、跟进、课程、班级和教练的 synthetic demo 数据与初始化脚本。
- 8 个 Tool：查询、推荐、评分、Lead 创建、互动写回和跟进任务创建。
- 基于年龄、水平、时间、预算和容量的确定性课程推荐。
- 基于试听评分、互动最近度、互动频次与调用方输入信号的确定性 Lead Score。
- CRM 互动的低信息、完全重复与近重复保护。
- Coze Multi-Agent（主控、招生线索、课程顾问、转化跟进）在 Preview / Debug 中人工完成六条核心 E2E Flow。
- 独立的 CoachFlow Concierge Single Agent，已接入乒乓球知识库、`get_course_info` 与 `recommend_courses`。
- Volcano Engine Knowledge Base / RAG 已用于 Coze Agent 的稳定业务知识检索。
- 两个 Golden Case 工作簿：12 条核心用例和 36 条补充用例。

## Evidence 与当前限制

数据库记录、课程和 CRM 客户均为虚构 Demo 数据。仓库没有真实客户、真实机构合作、商业营收、转化率或人工节省数据，因此不对这些结果作任何主张。

六条核心路径已在 Coze Preview / Debug 中以 synthetic demo data 人工完成 E2E 验证：指定课程动态查询、CRM 客户分析、已有客户写回、新客户建档、新客户首次咨询写回，以及 HITL 跟进的确认 / 取消分支。该证据不代表 production deployment、真实客户效果、自动化 trace evaluation 或线上 SLA；这些仍是上线前工作。

上述六条路径属于 Staff Copilot。Customer Concierge 当前只声明已创建独立 Single Agent 并完成知识库与两个课程 Tool 的接入；不将 Staff 侧验证结果外推为 Customer 侧成功率。Customer Lead Capture、真实渠道身份与跨端归因仍待设计。

## Resume-ready bullets

完整的 Bad Case → Trace → Root Cause → 最小修改 → 回归过程见 [Agent Iteration Story](agent-iteration-story.md)，涵盖路由、过度执行、近重复、参数类型、HITL、评测与动态信息查询。每项分别标注源码证据、人工 Coze 记录与尚待补充的 trace。

- 设计“Shared Business Layer + Two Agent Experiences”的少儿培训转化系统，以 Multi-Agent 服务员工复杂任务、Single Agent 服务家长窄任务。
- 规划 Persona、RAG、结构化业务 Tool、SQLite source of truth 与 HITL 的分工，隔离家长端和员工端的数据及操作权限。
- 以 Golden Case 与 Debug trace 定位路由、Tool 契约和过度执行问题，迭代停止条件及 CRM 写入 guardrail，并在 Coze Preview 人工验证核心路径；回归同时关注重复漏拦与新事实误拦。

## Interview 60-second pitch

CoachFlow 是面向少儿培训机构的 AI lead conversion system。家长需要回答“孩子适合什么课”，员工需要回答“今天跟谁、怎么推进”，所以我把产品拆成共享业务层上的两个体验：Concierge 用 Single Agent 完成咨询与课程匹配，Copilot 用 Multi-Agent 处理 CRM、试听、评分和跟进。稳定知识来自 RAG，实时名额和 CRM 事实来自 Tool，高风险跟进必须 HITL。当前 Staff 核心流程已用虚构数据人工验证；Customer 端已建立独立原型，生产身份、受控 Lead Capture 和线上评测是下一步。

## STAR / Deep Dive Talking Points

### 1. 为什么采用 Multi-Agent，而不是一个全能 Agent？

因为线索分析、课程推荐和转化跟进的目标、所需事实和风险不同。主控只路由，专项 Agent 只拿完成职责所需的 Tool，降低提示词冲突和越权范围。

### 2. 为什么 RAG 与 CRM Tool 必须分离？

训练原则和 FAQ 可以有一定时效滞后；名额、价格、客户互动不可以。把动态事实放在 Tool 中，能够让答案可追溯到当前数据库状态。

### 3. 如何控制 hallucination？

不让模型补充动态事实；课程、客户、试听和名额都由 Tool 返回。模型只根据返回事实解释，并在数据不足时说明不足。

### 4. 为什么 Lead Score 不直接交给 LLM？

当前 V1 使用可复现的确定性规则，便于检查输入和拆分分数。LLM 可以提取调用方明确给出的信号，但不应无依据地输出一个看似精确的分数。

### 5. 如果上线给真实机构，下一步做什么？

优先做身份解析与确认、RBAC、审计日志、可观测性、线上 Golden Case 评测和真实工作流的人工复核，再评估与教务/CRM 系统的集成，不先增加更多 Agent 或自动化写操作。
