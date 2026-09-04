# Evaluation

## 当前证据

`evals/` 中保存两份 Golden Case 工作簿：

| 文件 | 用途 |
| --- | --- |
| `coachflow_golden_cases_v1_core_12.xlsx` | 12 条核心场景 |
| `coachflow_golden_cases_v1_additional_36.xlsx` | 36 条补充场景 |

这些用例用于检查路由、Tool 调用、实体识别、RAG、澄清、线索分析和 HITL 安全。它们是测试资产，不是 RAG 知识源。

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

只看最终回答不能可靠证明 Agent 走过正确的 Tool 路径。例如，一个回答可能看似给出了正确名额，却没有调用 `get_course_info`。因此开发阶段建议把以下三者一起作为证据：

```text
Golden Case + visible execution trace + final answer
```

当前仓库不主张已经具备正式 Coze evaluator、线上成功率或生产监控分数。若要形成可比较的量化结果，需要先在可观察的执行环境中固定输入、保存 Tool trace，并定义每类用例的通过条件。

## CRM writeback checks

后端已验证的写入质量规则包括：

- 新 Lead 的精确身份去重与信息不足拒绝；
- interaction 的空白规范化与低信息过滤；
- 同 Lead、同渠道、10 分钟窗口内的完全重复拦截；
- 0.90 `SequenceMatcher` 近重复拦截；
- 预算、时间、意愿改变等新业务事实仍可写入。

## Future evaluation work

1. 将 Golden Case 转为可重复运行的 Agent 测试套件。
2. 保存路由、检索、Tool 调用和最终回答的 trace。
3. 增加失败分类：错误路由、缺失 Tool、错误实体、未 grounding、HITL 违规。
4. 在真实机构试点前定义人工复核采样和隐私处理规则。
