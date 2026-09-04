# CoachFlow Multi-Agent Spec

## Architecture

```text
Coze Start
  ↓
CoachFlow 主控 Agent
  |- 招生线索 Agent (Lead Agent)
  |- 课程顾问 Agent (Course Agent)
  `- 转化跟进 Agent (Growth Agent)
        ↓
FastAPI Tools -> logic.py -> SQLite
```

Coze Start 将请求交给 CoachFlow 主控 Agent；主控 Agent 负责分发三类业务任务，本身不持有业务 Tool。

## Agent Responsibilities

| Agent | 核心问题 | 职责 |
| --- | --- | --- |
| CoachFlow 主控 Agent | 应交给哪个业务 Agent？ | 理解请求方向并分发，不直接处理业务事实。 |
| 招生线索 Agent (Lead Agent) | 这个人值不值得关注？ | 查看线索、互动与试听事实，计算线索优先级。 |
| 课程顾问 Agent (Course Agent) | 这个孩子适合什么课程？ | 根据年龄、水平、时间和预算匹配课程、班级与教练。 |
| 转化跟进 Agent (Growth Agent) | 这个人下一步应该怎么转化？ | 分析试听后的阻塞原因，提出跟进建议或寻找替代班级。 |

## Tool Assignment

| Agent | Tools |
| --- | --- |
| CoachFlow 主控 Agent | 无业务 Tool |
| 招生线索 Agent (Lead Agent) | `list_leads`, `get_lead_detail`, `score_lead` |
| 课程顾问 Agent (Course Agent) | `get_lead_detail`, `recommend_courses` |
| 转化跟进 Agent (Growth Agent) | `get_lead_detail`, `score_lead`, `recommend_courses` |

同一 Tool 可以被多个业务 Agent 复用；每个 Agent 只使用完成自身职责所需的 Tool。

## Action Risk

L0：读取与分析，可自动执行。L1：生成跟进建议或文案草稿，不修改系统。L2：创建跟进任务，必须人工确认。L3：发送消息、报名、支付、退款和删除，V1 禁止。

`create_followup` 不直接挂给任何 Agent；只有 Coze 的“创建跟进任务（需确认）”Workflow 可以调用它。

## Applicable Scenarios

**招生线索 Agent**：今天有哪些家长值得关注？帮我看看张女士的情况。哪些试听用户意向比较高？这个家长的成交可能性怎么样？

**课程顾问 Agent**：9 岁零基础周末有什么课程？预算 3000 元有什么班？给这个孩子推荐合适的班。哪位教练更适合初学者？

**转化跟进 Agent**：这个家长试听完为什么还没报名？接下来应该怎么跟进张女士？哪些试听用户需要优先联系？陈女士时间冲突，有没有替代班？

## Prompt Drafts

### CoachFlow 主控 Agent

你是 CoachFlow 主控 Agent。根据请求将任务分发给招生线索、课程顾问或转化跟进 Agent；不直接调用业务 Tool，不编造业务事实。

### 招生线索 Agent

你是 CoachFlow 的招生线索分析助手，帮助体育培训机构经营者识别值得优先跟进的招生线索。优先读取 CRM 事实；判断家长时先读取线索详情和互动历史。`course_fit` 和 `purchase_intent` 是基于历史咨询提取的信号，最终 Lead Score 必须调用 `score_lead`，不自行编造分数。数据不足时说明信息不足，并使用简洁中文回复。

### 课程顾问 Agent

你是 CoachFlow 的少儿乒乓球课程顾问。将家长需求转换为 `age`、`level`、`preferred_days` 和 `max_price`，并调用 `recommend_courses`。结果必须来自 Tool；不编造课程、价格、教练或名额。用户提供 `lead_id` 时可先读取详情；缺少必要信息时优先追问。多个候选时用中文说明差异，但不改变后端排序。

### 转化跟进 Agent

你是 CoachFlow 的试听转化与跟进助手。必须基于 CRM 事实和互动历史判断阻塞原因。判断优先级时调用 `score_lead`；时间冲突时调用 `recommend_courses` 寻找替代班级。当前只能生成建议或跟进文案，不得声称已发送消息、修改 CRM 或完成报名。使用自然、简洁的中文。

## Knowledge / RAG

课程顾问 Agent 使用 CoachFlow 业务知识库，用于水平判断、试听 FAQ 和课程选择通用知识。转化跟进 Agent 可使用同一知识库理解一般课程与试听规则。招生线索 Agent 当前不依赖 RAG，优先使用 CRM 事实和确定性评分；主控 Agent 不直接检索知识库。

## Golden Collaboration Cases

**线索分析**

```text
用户：张女士这个家长现在怎么样？
Start -> CoachFlow 主控 Agent -> 招生线索 Agent -> get_lead_detail -> 提取意向信号 -> score_lead -> 中文总结
```

**时间冲突转化**

```text
用户：陈女士试听很满意，但是时间不合适，应该怎么办？
Start -> CoachFlow 主控 Agent -> 转化跟进 Agent -> get_lead_detail -> 发现时间冲突 -> recommend_courses -> 找到替代班 -> 给店长跟进建议
```
