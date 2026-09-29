# Handoff

Generate a compact view from `PROJECT.md`, `CONTROL.json`, `STATE.json`, the active Work Unit, the machine Result Envelope, and relevant Evidence. The Result Envelope is the authoritative structured fact source; Handoff and GPT Return Text are derived views and must never become competing sources of truth. A return-required envelope must carry `SOURCE_PROJECT_CONTEXT_ID`, `SOURCE_PROJECT_NAME`, and `FRAMEWORK_VERSION`, and GPT must verify the source identity before accepting it.

Result classification is owned by the Result Envelope's `result_message_type` field. `REVIEW_RESULT`, `REVIEW_FINDING`, and `IMPLEMENTATION_RESULT` are result-side values only; protocol failures may use `INVALID_INSTRUCTION` or `ROLE_AUTHORITY_CONFLICT`. The Instruction Envelope alone owns `instruction_type`, and no generic `message_type` field exists. A `REVIEW_FINDING` is evidence only and never becomes executable or authorizes a fix; GPT/User remediation must produce a new `FIX_INSTRUCTION`.

Role and correlation fields (`responder_role`, `return_role`, `response_to_instruction_id`, `review_target_revision`, `finding_ids`, `fix_round`, `artifact_stage`, and `artifact_path`) are projected from the Result Envelope. Uppercase Return/Handoff labels are presentation derived from those machine facts and cannot grant execution authority.

When available, include these derived navigation/resume keys to route the next read efficiently: `MAP_ROUTE`, `MAP_MODULES`, `MAP_STALE_MODULES`, `MAP_MISSING`, `RESUME_MODE`, `RESUME_CHECKPOINT_REVISION`, `RESUME_ANCHOR_SHA`, `HOT_MODULES`, `HOT_FILES`, `CONTEXT_INVALIDATED`, and `NEXT_REQUIRED_READS`. These keys are derived routing context only and must not override CONTROL, STATE, Work Unit, Result, Evidence, source/tests, or Git/GitHub facts.

When `Return To GPT Required = YES`, Codex's final output must include one independent, self-contained plain-text GPT Return Text generated from that Result Envelope. It must be directly copyable and must contain the complete stable sections:

`RESULT`, `WORK_UNIT`, `STATE_REVISION`, `EXECUTION`, `CHANGED`, `VERIFY`, `EVIDENCE`, `DEVIATIONS`, `BLOCKERS`, and `NEXT_GPT_ACTION`.

When applicable, also include Git Base / Implementation SHA, Parallel Batch / Execution Unit, Observability / Fitness, and Extension Evidence references. Missing or empty fields are written as `NONE`. Raw logs, full diffs, telemetry, debug traces, and intermediate reasoning are not part of the Return Contract; provide them only through Evidence references.

The same complete field set is required for `PASS`, `FAIL`, and `BLOCKED`, so GPT can determine the next authorized action from the copied text alone.

For GitHub continuity, Handoff must label `LATEST_SYNCED_REMOTE_STATE` and
`LOCAL_UNSYNCED_STATE` separately. GPT validates the selected repository ID
and independently re-observes the target remote ref/head before accepting a
publication. A new mutating Work Unit requires clean preflight; local
degraded continuation is limited to the same already-authorized active Work
Unit and cannot produce formal `PASS`.
