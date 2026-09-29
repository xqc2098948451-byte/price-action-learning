# Shared Contracts

第一版只冻结以下五个共享契约及其最小字段，不在本 Work Unit 增加字段。

## StudyContext

```text
current_stage
primary_skill
current_focus_error
allowed_concepts
forbidden_concepts
concept_confidence
reviews_due
evaluation_policy
```

## TrainingAttempt

```text
id
created_at
stage
image_reference
user_analysis
user_confidence
revision
status
```

`user_analysis` 为初始分析，一旦提交不得覆盖；`revision` 最多一次。

## Evaluation

```text
attempt_id
what_was_correct
primary_issue
primary_error
contributors
hint
skill_signal
evaluation_confidence
abstain
```

每次最多一个 `primary_error`、最多两个 `contributors`；低置信或信息不足时允许 `abstain`。

## LearningState

```text
current_stage
skills
errors
current_focus
reviews_due
```

## ReviewRecord

```text
id
source_attempt_id
error_id
scheduled_for
completed_at
new_analysis
result
```
