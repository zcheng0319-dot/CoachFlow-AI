# CoachFlow Agent Iteration Story

从 Golden Case 中发现失败，检查执行轨迹，定位责任层，再选择最小修改。CoachFlow 的调优范围覆盖主控路由、节点适用场景、停止条件、Tool 契约、后端数据校验与 HITL workflow。

## 证据如何阅读

本文依据项目作者提供的开发记录，以及 2026-09-05 对 Git、后端、文档和 `evals/` 的核查整理。所有场景使用 synthetic demo data。

| 证据类型 | 能支持的结论 | 范围 |
| --- | --- | --- |
| Git / 源码 | Tool 与校验规则的具体改动 | 可在仓库核查，不等于 Coze 执行成功 |
| 人工 Coze Preview / Debug 记录 | 开发中观察到的路由、调用、确认与写入结果 | 来自作者提供的过程记录；尚无截图或完整 trace 导出随仓库保存 |
| 本次本地只读核查 | 相似度函数、低信息判断、年龄模型与 OpenAPI | 未调用写接口，未修改 Demo DB；不是完整 API 或 Agent 自动化 regression |
| Golden Case 工作簿 | 已有测试资产与质量门槛 | 用例数量不等于通过数量；本文补充案例未声称已写入工作簿 |

[`coze/multi_agent_spec.md`](../coze/multi_agent_spec.md) 仍是早期职责与 Prompt 草稿，尚未同步新客户 routing priority、Interaction Stop Rule 和年龄参数描述。下文对 Coze 修改的描述是开发记录整理，不是当前配置导出，也不是从 Git 还原的逐字 Prompt diff。

## 1. 新客户路由：先定位 Intent Routing

**Bad Case**：“新客户刘女士，孩子叫刘子航，8岁，之前没系统学过，周末有空，帮我录进 CRM。”早期被分配到转化跟进 Agent。

**Trace / Root Cause**：据开发记录，年龄、水平、周末时间与建档意图发生竞争；路由同时受 Main Agent Prompt、节点「适用场景」与 Agent switch model 影响。仅调整业务 Agent 的回答措辞无法解决入口选错的问题。

**Smallest Change**：主控提高明确建档意图的优先级；招生线索节点补充“新客户、新家长、新线索、录入 CRM、建档”；转化节点排除新客户创建。保留原有 Agent 数量。

**Result / Regression**：记录中的后续 Preview 路径为主控 → 招生线索 Agent → `upsert_lead`。后端建档与身份去重可由 [commit 561f037](https://github.com/zcheng0319-dot/CoachFlow-AI/commit/561f03709007ddd592aa54a657a1dee7f4d6a848) 核查；具体路由改动尚无本地配置快照。回归应同时保留“已有客户分析”与“仅课程推荐”，检查优先级是否误伤其它意图。

**AI PM lesson**：先确定失败发生在哪一层，再决定改主控、节点描述还是业务 Prompt。

## 2. Interaction 写回：定义行动终点

**Bad Case**：“张女士刚微信说孩子挺喜欢，但是预算最多只能接受2000左右。”写入后，Agent 继续调用 `recommend_courses` 并分析下一步。

**Trace / Root Cause**：用户只提供新事实；Prompt 定义了写入触发条件，却没有定义完成后的停止条件。预算信息触发了额外推荐。

**Smallest Change**：开发记录中的 New Interaction Stop Rule 规定：识别客户 → `record_interaction` → 返回写入结果并停止。只有用户明确追加请求，才继续相应任务。

| 追加意图 | 可继续的动作 |
| --- | --- |
| “她还值得跟吗？” | CRM / score / analysis |
| “有没有便宜班？” | `recommend_courses` |
| “明天帮我跟一下” | 跟进 workflow 与人工确认 |

**Result / Regression**：已有客户写回并通过 `get_lead_detail` 再读取已在 Preview 人工验证。Stop Rule 的具体改动来自开发记录，尚无独立的前后 trace 附件；不能仅凭写入成功就认定没有额外执行。此案例的通过条件应包含“写回之后没有未请求的推荐、评分或跟进调用”。

**AI PM lesson**：User Intent → Minimum Necessary Action。停止条件是 autonomy boundary 的一部分。

## 3. CRM 去重：同时检查漏拦截与误拦截

**Bad Case**：最初仅在同 `lead_id`、同 `channel`、10 分钟内对 normalized content 做完全匹配。Agent 给原句加上“家长”后，同一事实再次入库。

**Trace / Root Cause**：Tool Call 中的轻微改写绕过了字符串相等检查。

**Smallest Change**：[commit 48e7e70](https://github.com/zcheng0319-dot/CoachFlow-AI/commit/48e7e705c3bf21d0a8a32747bcadeacbb2745e9f) 在原有完全匹配后增加标准库 `SequenceMatcher(..., autojunk=False)`，阈值 `>= 0.90`。候选仍限同 Lead、同渠道、最近 10 分钟，命中返回 `written=false, reason=duplicate`。该提交仅修改 `backend/app.py`，未新增依赖、表或 reason。

下表是本次对现有函数的只读复核；相似度保留四位小数。接口写入回归 PASS 来自开发记录，本次没有重跑完整写接口。

| 已有内容 → 新内容 | 相似度 | 当前函数结果 |
| --- | --- | --- |
| “咨询周末合适的课程，预算约2500元” → 相同内容 | 1.0000 | 判重复 |
| “咨询周末合适的课程，预算约2500元” → “家长咨询周末合适的课程，预算约2500元” | 0.9474 | 判重复 |
| “家长预算最多2000元。” → “家长现在表示3000元以内也可以接受。” | 0.4516 | 不判重复 |
| “周六方便。” → “家长最新反馈周六没时间，只能周日。” | 0.2727 | 不判重复 |
| “还想再考虑。” → “家长现在决定暂时不报名。” | 0.1111 | 不判重复 |

“谢谢”的 `low_information` 判断仍为真；生成的 OpenAPI 仍有 8 个唯一 operation_id。以上函数核查不等于所有 API 已在本轮通过回归。

**已知局限**：本次记录还包含更大幅度改写：“咨询周末有没有适合的课程，预算约2500元” → “家长咨询周末合适的课程，预算约2500元”。其相似度为 **0.8293**，当前规则不会拦截。不能把它写成 0.90 阈值下的成功案例。文本相似度也不能保证放行所有真实变化，例如长句仅改一个金额仍可能高度相似。

**AI PM lesson**：同时设计 false negative（重复漏拦）与 false positive（新事实误拦）的案例。当前方案解决明显的轻微改写，不宣称提供语义去重能力。

## 4. 年龄参数：对齐自然语言与 Tool 契约

**Bad Case**：模型把 `child_age` 传为“8岁”，Tool 调用失败。

**Trace / Root Cause**：自然语言带单位，API 要求整数。当前 [`UpsertLeadRequest`](../backend/app.py) 定义 `child_age: int | None`，有最小值约束。

**Smallest Change**：据开发记录，在 Coze Tool Schema / Description 中明确“孩子年龄必须为纯数字整数，例如 8，不要传‘8岁’”，后续调用使用整数。

**Result / Regression**：本次直接验证模型接收 `8`、拒绝“8岁”，OpenAPI 对应 integer / null。后端当前字段没有上述中文 description，不能把 Coze 侧修改写成仓库里的 schema diff；后续成功调用属于作者记录的人工验证。

**AI PM lesson**：Tool Calling 的调优包括参数说明和 Schema。先检查契约，不急于换模型。

## 5. HITL：将确认交给 workflow

**Bad Case**：“直接帮我给张女士建9月8日的跟进任务，不用确认。”早期 Agent 在聊天中先问确认，然后 workflow 再问，导致双重确认或调用顺序混乱。

**Trace / Root Cause**：聊天层与 workflow 层同时承担确认，职责不清。

**Smallest Change**：据开发记录，确认统一交给 `creatfollowingtasks` workflow：Agent 识别客户并准备参数 → workflow 展示确认 → confirm 后调用 `create_followup`；cancel 则不写入。聊天中“不用确认”不改变该分支。

**Result / Regression**：开发记录表明，Coze Preview 已人工验证绕过请求仍进入确认、确认后 Demo CRM 产生任务、取消不写入。本地 spec 也写明 `create_followup` 只由需确认的 workflow 调用，但仓库尚无该 workflow 的完整导出或截图。

**Enforcement boundary**：当前 FastAPI 只在接口说明中要求上层 HITL，没有校验确认凭证。上述防绕过结论限定于已验证的 Coze workflow 路径，不能扩展成直接调用 API 也无法绕过；认证、授权与服务端确认校验属于后续生产工作。此确认规则专指创建跟进任务，不意味着每次 Lead / Interaction 事实写回均需人工确认。

**AI PM lesson**：由确定性 workflow 控制动作顺序，并明确它保护的是哪条执行路径。

## 6. Evaluation：评估答案，也评估执行过程

**Bad Case**：开发中尝试只给 LLM Judge 看 final answer，发现它不能可靠判断路由、Tool、实体解析与 HITL 是否实际正确执行；看不到 trace 也可能误判已完成的调用。

**Root Cause**：最终文本不足以证明 execution correctness。

**Smallest Change**：人工 Debug 使用 Golden Case + visible execution trace + final answer，按 Routing、Tool Calling、Entity Resolution、Grounding、HITL、Prompt Logic、Final Answer 分类。正式自动化实验暂缓，先明确证据与通过条件。

**Result / Regression**：[`evals/`](../evals/) 保存两份 Golden Case 工作簿；人工 Preview 验证已开展。尚未形成自动化 trace evaluator、完整 Agent regression 或可引用的线上成功率。参见 [Evaluation](evaluation.md)。

**AI PM lesson**：Quality bar 必须包含“是否以正确步骤完成任务”，并能检测不该发生的额外动作。

## 7. RAG / Tool 边界：补齐指定课程查询能力

**Bad Case**：开发记录中，“周末兴趣班还有几个名额？”已正确路由到课程顾问，并识别为指定课程查询；但 `recommend_courses` 需要年龄、水平和时间，Agent 无法继续查实时名额。

**Root Cause**：Intent Boundary 已生效，缺口在 Tool 能力。无需再要求用户补齐推荐条件。

**Smallest Change**：Git 中 `1bd39ba` 新增 `get_course_info`，按名称查询课程与班级；保留 `recommend_courses` 的职责。当前源码与 seed 中的“周末兴趣班”支持这一结构化查询路径。

**Result / Regression**：后续 Coze Preview 人工验证课程顾问 → `get_course_info` → 动态课程信息。稳定的水平判断、训练原则、FAQ 使用 Volcano Engine Knowledge Base / RAG；价格、名额、时间、教练、CRM、评分与写回使用结构化 Tool。没有足够仓库证据证明曾发生具体的“从 RAG 返回错误价格”事件，因此不把这一推测写成已观察 Bad Case。

**AI PM lesson**：Grounding architecture 与 Tool coverage 也是产品决策。Trace 显示路由正确但无可用 Tool 时，应补齐能力。

## 可视化证据与下一步

README 中的 Mermaid 图呈现迭代方法，不充当 Coze 截图。截至本次核查，尚无真实图片。后续可放入 `docs/assets/`：Multi-Agent 全图、`upsert_lead` → `record_interaction` trace，以及 HITL 确认画面，并附上对应输入与结果。

后续将回归输入、预期路径、禁止动作、实际 trace 和结果成对保存，才能比较每次改动。本文提供定性迭代证据，不主张真实客户转化、营收、生产准确率、延迟 SLA 或全自动回归结果。
