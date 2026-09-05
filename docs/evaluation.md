# Evaluation

## 当前证据

`evals/` 中保存两份 Golden Case 工作簿：

| 文件 | 用途 |
| --- | --- |
| `coachflow_golden_cases_v1_core_12.xlsx` | 12 条核心场景 |
| `coachflow_golden_cases_v1_additional_36.xlsx` | 36 条补充场景 |

这些用例用于检查路由、Tool 调用、实体识别、RAG、澄清、线索分析和 HITL 安全。它们是测试资产，不是 RAG 知识源。

此外，Staff Copilot 的六条核心路径已在 Coze Preview / Debug 中以 synthetic demo data 人工完成 E2E 验证。Customer Concierge 已建立独立 Single Agent 并接入知识库、`get_course_info` 和 `recommend_courses`；当前不将 Staff 的验证结果外推为 Customer 侧效果。这些证据不等于 production deployment，也不等于已具备自动化回归。

## Two-experience evaluation boundary

| Experience | 核心检查 |
| --- | --- |
| Staff Copilot | Multi-Agent 路由、CRM grounding、实体识别、写回质量、HITL 与不应发生的额外动作 |
| Customer Concierge | Single Agent 回答边界、课程 Tool 调用、动态事实 grounding、澄清质量与 CRM 权限隔离 |

两个 Experience 共享部分课程 Golden Case，但权限和任务完成标准必须分开。Customer Concierge 不应调用 CRM 客户查询、Lead Score、Interaction Writeback 或 Follow-up。

## 当前质量门槛

| 维度 | 需要验证的问题 |
| --- | --- |
| Routing correctness | 请求是否交给正确的专项 Agent？ |
| Tool-call correctness | 是否调用了必要且正确的 Tool？ |
| CRM grounding | 客户、试听、互动和分数是否来自 CRM 事实？ |
| Dynamic-fact grounding | 价格、班次、名额和教练是否来自实时 Tool？ |
| RAG boundary | 稳定知识是否来自知识源，而非虚构？ |
| HITL compliance | 跟进等风险动作是否先获得确认？ |
| Write quality | 低信息、完全重复与近重复内容是否被拦截？ |

## Evaluation lesson

开发中已经发现：只让 LLM Judge 观察最终回答，无法可靠判断 Tool 是否真的被调用；看不到 trace 也可能误判正确调用。人工 Debug 阶段因此同时观察 Routing、Tool Calling、Entity Resolution、Grounding、HITL、Prompt Logic 与 Final Answer：

```text
Golden Case + visible execution trace + final answer
```

当前尚无正式 Coze evaluator、自动 trace evaluation、线上成功率或生产监控分数。若要形成可比较的量化结果，需要先在可观察的执行环境中固定输入、保存 Tool trace，并定义每类用例的通过条件。

具体失败、责任层与最小修改见 [Agent Iteration Story](agent-iteration-story.md)。回归同时检查应发生与不应发生的动作：仅提供新事实时，写回后不应继续推荐或评分；取消跟进时，不应出现创建任务的调用。

## CRM writeback checks

后端已验证的写入质量规则包括：

- 新 Lead 的精确身份去重与信息不足拒绝；
- interaction 的空白规范化与低信息过滤；
- 同 Lead、同渠道、10 分钟窗口内的完全重复拦截；
- 0.90 `SequenceMatcher` 近重复拦截；
- 预算、时间、意愿改变等新业务事实仍可写入。

上述结论针对已验证样例。2026-09-05 的只读复核确认：加“家长”的原始近重复样例相似度为 0.9474；更大改写“咨询周末有没有适合的课程…”与“家长咨询周末合适的课程…”仅为 0.8293，不会命中 0.90 阈值。高相似文本也可能包含真实事实变化，因此不能把规则当作语义去重保证。具体输入及核查范围见迭代记录；本轮没有重跑写接口或自动化 Coze regression。

## Future evaluation work

1. 将 Golden Case 转为可重复运行的 Agent 测试套件。
2. 保存路由、检索、Tool 调用和最终回答的 trace。
3. 增加失败分类：错误路由、缺失 Tool、错误实体、未 grounding、HITL 违规。
4. 在真实机构试点前定义人工复核采样和隐私处理规则。
