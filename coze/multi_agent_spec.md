# CoachFlow Agent Experience Spec

CoachFlow 采用 **Shared Business Layer + Two Agent Experiences**。本文件记录产品职责与权限边界，不是 Coze 线上配置导出。

## Experience A — CoachFlow Copilot

**Internal Staff Copilot**

服务机构老板、店长、招生顾问和课程顾问。核心问题是：“今天我应该关注哪个客户，以及下一步应该做什么？”

```text
Coze Start
  ↓
CoachFlow 主控 Agent
  ├─ 招生线索 Agent
  ├─ 课程顾问 Agent
  └─ 转化跟进 Agent
        ↓
Shared Business Tools → SQLite CRM
```

### Agent Responsibilities

| Agent | 核心问题 | 职责 |
| --- | --- | --- |
| CoachFlow 主控 Agent | 应交给哪个业务 Agent？ | 理解员工意图并分发，不直接处理业务事实 |
| 招生线索 Agent | 哪个客户值得关注？ | CRM 查询、新 Lead 创建、互动与试听读取、Lead 优先级 |
| 课程顾问 Agent | 哪个课程合适？ | 课程推荐、指定课程动态信息与教练支持 |
| 转化跟进 Agent | 为什么没报名，下一步怎么推进？ | 阻塞分析、Interaction Writeback、建议与 HITL Follow-up |

新客户、新家长、新线索、录入 CRM 或建档意图优先路由到招生线索 Agent，即使同一句包含年龄、预算、时间或课程需求。转化跟进 Agent 排除新客户创建场景。

只提供客户最新事实时，写入 `record_interaction` 后停止。只有用户进一步要求评分、推荐或跟进时，才调用相应能力。

## Experience B — CoachFlow Concierge

**Customer-facing AI Course Consultant**

服务潜在家长和潜在学员；已有学员家长属于未来扩展。核心问题是：“我的孩子适合学什么，以及下一步应该怎么开始？”

Concierge 使用独立 **Single Agent**，当前连接：

- CoachFlow 乒乓球知识库；
- `get_course_info`；
- `recommend_courses`。

它可以回答一般训练问题、辅助大致水平判断、解释课程选择、查询当前课程信息并推荐课程。它不访问其他客户信息、内部销售标签、Lead Score、员工跟进策略或内部销售优先级。

Customer task space 当前为“咨询 → 水平判断 → 课程匹配 → 课程信息确认”。采用 Single Agent 可减少路由错误、token 成本、延迟和 context handoff。**Architecture follows task complexity, not hype.**

## Shared Business Layer

| Layer | Responsibility |
| --- | --- |
| Volcano Engine Knowledge Base | 水平判断、训练原则、FAQ 与稳定业务知识 |
| FastAPI Structured Tools | 当前课程、价格、名额、教练、CRM、Lead、Interaction、Lead Score 与 Follow-up |
| SQLite prototype | 当前 structured source of truth；production 方向为 PostgreSQL |

动态价格、名额、时间、教练与 CRM 事实必须来自 Tool，不由知识库或 Agent 记忆补全。

## Capability Assignment

| Capability / Tool | Staff Copilot | Customer Concierge |
| --- | ---: | ---: |
| Knowledge / RAG | ✅ | ✅ |
| `get_course_info` | ✅ | ✅ |
| `recommend_courses` | ✅ | ✅ |
| `list_leads` | ✅ | ❌ |
| `get_lead_detail` | ✅ | ❌ |
| `score_lead` | ✅ | ❌ |
| `record_interaction` | ✅ | 暂不直接开放 |
| `upsert_lead` | ✅ | Future controlled lead capture |
| `create_followup` | ✅ + HITL | ❌ |

## Action Risk

L0：Persona 权限内的知识与数据读取，可自动执行。

L1：解释、课程建议或跟进文案草稿，不修改系统。

L2：CRM 事实写入与 Follow-up，仅 Staff Copilot 可用；`create_followup` 由 Coze 跟进 workflow 确认后调用。

L3：发送消息、报名、支付、退款和删除，V1 禁止。

用户要求“不用确认”不能跳过 Follow-up workflow 的确认分支。Cancel 不写入。当前后端没有确认凭证校验，该保证只适用于已配置并人工验证的 Coze workflow 路径。

## Knowledge / RAG

两个体验可以使用同一 CoachFlow 业务知识库。Concierge 用于家长训练咨询和水平判断；Staff Copilot 中的课程、转化任务可用它理解一般规则。CRM 事实与实时课程数据始终由结构化 Tool 提供。

## Evidence Boundary

Staff Copilot 的指定课程查询、CRM 客户分析、已有客户写回、新客户建档、新客户首次咨询写回，以及 HITL 确认 / 取消分支，已在 Coze Preview / Debug 使用 synthetic demo data 人工验证。

Customer Concierge 已在 Coze 创建为独立 Single Agent，并接入知识库、`get_course_info` 和 `recommend_courses`。本文不主张 production 上线、真实客户效果、自动化回归或线上 SLA。
