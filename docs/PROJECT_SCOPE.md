# Project Scope

第一版遵循最小闭环，只覆盖 Learning Map、Training、Evaluation、Learning State、Review，以及作为入口层的 Study Entry。当前 MVP 为 S1–S3，不纳入 S4–S8。

## Learning Map

保存 Stage、Skill、Concept、Error mapping、Knowledge Boundary 和 Knowledge Confidence。知识置信度仅有 `CORE`、`CONTEXTUAL`、`CONTESTED`：

- 只有 `CORE` 且在当前 Stage `Allowed` 的知识可以作为正式判错依据。
- `CONTEXTUAL` 可以辅助解释，不能单独判错。
- `CONTESTED` 默认不得进入核心训练。

Learning Map 不保存完整技术分析教材。GPT 使用自身已有知识进行最小解释。

## Training

截图 → 用户 Initial Analysis → Confidence → 锁定 Initial Analysis → GPT Diagnostic Feedback → 最多一次 Revision → Final Evaluation。

## Evaluation

用户先分析，GPT 后评价。GPT 评价分析过程，不负责预测行情，也不根据后来行情结果倒推对错。

最少输出 `what_was_correct`、`primary_issue`、`primary_error`、`contributors`、`hint`、`skill_signal`、`evaluation_confidence`、`abstain`。每次最多一个 Primary Error、最多两个 Contributors。低置信或信息不足时允许 Abstain。

## Learning State

保存 `current_stage`、`skill_states`、`error_states`、`current_focus`、`review_schedule`。

Skill 状态仅有 `NOT_STARTED`、`LEARNING`、`UNSTABLE`、`STABLE`。Error 状态仅有 `NEW`、`REPEATED`、`FOCUS`、`IMPROVING`、`RESOLVED`。

## Review

第一版复盘间隔为 3 天、7 天、30 天。复盘时必须隐藏旧答案和旧 GPT 点评，用新的独立分析验证错误是否改善。

## 边界

本 Work Unit 只建立项目基础和领域契约，不开发业务功能。不引入 Web UI、Dashboard、数据库、API Server、TradingView API、自动交易代码、指标系统、复杂插件实现、示例应用或未批准的框架代码。
