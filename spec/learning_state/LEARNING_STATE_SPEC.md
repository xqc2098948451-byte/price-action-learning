# Learning State Core — Conservative Evaluation Recording

## Ownership and authority

Learning State records already-authorized structured feedback from a submitted
TrainingAttempt and its Evaluation. It owns current Stage, Skill states, Error
states, current focus and preserved due-review references. Training owns original
submission provenance; Evaluation owns diagnostic judgment and historical Error
eligibility; Review will own scheduling, improvement, resolution and stability.

Published Training, Evaluation, Learning Map and docs/CONTRACTS.md are read-only
dependencies at main 49ea8aeaed1ad5e734732ec7217a216192b16dfa. Identifier membership
and ordering follow Learning Map blob 726b35db8409ea03cbec33c916db7374e6724e03.
This module copies no Concept definitions, teaching content or Error-to-Concept
judgment rules. It neither interprets a market scenario nor re-evaluates analysis.

## Exactly five immutable fields

One frozen, slotted, factory-controlled LearningState has exactly these persistent
fields in the shared order, with no __dict__, hidden field or parallel record:

| Field | Canonical representation |
| --- | --- |
| current_stage | Exact base str: S1, S2 or S3. |
| skills | Exact tuple of three exact two-string tuples, in canonical Skill order. |
| errors | Exact tuple of unique exact Error/status tuples, in published Error-ID order. |
| current_focus | None or one exact canonical Error ID already represented in errors. |
| reviews_due | Exact tuple of nonempty base strings, opaque preserved references. |

Skill order is SKL-S1-MARKET-STATE, SKL-S2-STRUCTURE-MOVEMENT,
SKL-S3-MARKET-LOCATION. Every Skill occurs exactly once. Allowed Skill states are
NOT_STARTED, LEARNING, UNSTABLE and STABLE.

The exact published Error order is OBS-001, OBS-002, OBS-004, STR-001, STR-002,
STR-006, STR-007, STR-003, STR-004, STR-005, REA-002, REA-003, REA-005, LOC-001,
LOC-002, LOC-003, LOC-004, LOC-005, LOC-006. Allowed Error states are NEW, REPEATED,
FOCUS, IMPROVING and RESOLVED. Storage order differs from lexical sorting.

Canonical prior states may contain STABLE, IMPROVING, RESOLVED and nonempty
reviews_due so a later authorized Review can supply them. This implementation
does not make those decisions or add a public prior-state editing operation.
All stored members are immutable base strings; mutable containers and string
subclasses are rejected at the state validation boundary.

## Public API and initial creation

The package exports only LearningState, create_learning_state and apply_evaluation.

```python
create_learning_state(*, current_stage)
apply_evaluation(*, state, attempt, evaluation)
```

Initial creation requires one explicit Stage. It creates all three ordered Skills
as NOT_STARTED, errors=(), current_focus=None and reviews_due=(). There are no
history, score, counter, timestamp, focus override or scheduling parameters.

## Canonical inputs and original-submission binding

Application requires type(state) is LearningState, type(attempt) is the exact
published TrainingAttempt and type(evaluation) is the exact published Evaluation.
Duck types, record subclasses, missing fields, malformed mutable containers,
noncanonical IDs/statuses and equality-spoofed consumed values are rejected.
Require evaluation.attempt_id == attempt.id and state.current_stage == attempt.stage,
including abstention. Every rejection leaves all original inputs unchanged.

The pinned Evaluation module's read-only submission-shape validator consumes and
returns the supplied original TrainingAttempt. Learning State checks the exact
Stage and canonical observable state/Evaluation shapes before transitions. It
does not reconstruct a TrainingAttempt or Evaluation from matching caller fields.
Matching identity, timestamp or analysis is never provenance. Training's published
factory and standard reconstruction restrictions remain the supported boundary.
No Error eligibility or Skill derivation is rerun; Evaluation's already-authorized
skill_signal and formal Error fields remain the signal authority.

primary_issue, hint and what_was_correct are never parsed for Error IDs. Prose shape
checks do not interpret content. No natural-language classifier or new diagnostic
channel is introduced.

## Exact transition algorithm

Every successful application returns a new validated immutable state, preserving
current_stage and reviews_due. It changes no input object or submitted analysis.

Canonical current formal Error order is primary_error, if present, followed by
contributors in their stored tuple order. Only these fields supply formal Errors.

If abstain is true, all five fields remain semantically unchanged; no Skill,
Error, focus, Stage or review-scheduling transition occurs.

For non-abstaining Evaluation with at least one formal Error, change only the Skill
identified by skill_signal to UNSTABLE. Preserve every other Skill. With no formal
Error, transition that Skill exactly as follows:

| Prior | Result |
| --- | --- |
| NOT_STARTED | LEARNING |
| LEARNING | LEARNING |
| UNSTABLE | UNSTABLE |
| STABLE | STABLE |

One correct Evaluation never creates STABLE, advances a Stage, improves or resolves
an Error, or clears the old focus.

When formal Errors exist, determine repeated membership against previous errors
before updating anything. Select focus as the first current Error in canonical
Evaluation order that was already present in the previous state. If none repeats,
select primary_error if present, otherwise the first contributor. A repeated
contributor can therefore outrank a new primary; among repeated Errors, current
Evaluation order decides priority, rather than stored Error order.

Each current Error absent from previous errors becomes NEW, including a selected
first occurrence. A repeated selected Error becomes FOCUS; every other repeated
current Error becomes REPEATED. Recurrence from IMPROVING or RESOLVED returns to
FOCUS or REPEATED. Previous Errors absent from this Evaluation retain their exact
statuses, including unrelated FOCUS/IMPROVING/RESOLVED. Store the combined result in
the published 19-ID order without counters or history. Set current_focus to the
selected Error. A non-abstaining no-error Evaluation preserves errors and
current_focus unchanged while applying only the Skill rule above.

## Construction, immutability and restoration

Ordinary LearningState(...) construction is unsupported. __new__ rejects every
public argument shape; dataclasses.replace, copy.copy, copy.deepcopy, pickle at
every supported protocol, __reduce__, __reduce_ex__ and __setstate__ reject before
any state assignment. Standard pickle BUILD restoration cannot bypass the factory.
Rejection leaves the original record unchanged. No mutable caller alias is stored.

A module-private _build_state validates all five values before private allocation.
Internal regression tests may use it to supply canonical prior STABLE,
IMPROVING/RESOLVED and existing due references. It is not exported or a public
workflow. Explicit object.__new__, object.__setattr__, reflection/memory tampering
and private-internal abuse are outside the ordinary/public API threat model.
Malformed low-level fixtures can still be rejected by observable shape validation;
this does not turn copied fields into proof of original provenance.

## Review and process boundaries

Initial reviews_due is empty. Application preserves an existing canonical tuple
unchanged and assigns no scheduling meaning to its opaque strings. No ReviewRecord,
date arithmetic, 3/7/30-day intervals, improvement/resolution decision or Review
execution exists. The later Review Work Unit owns these responsibilities.

State records the analysis process reflected by canonical Evaluation. Public
operations accept no future candles, later price movement, realized P/L, trade
result, prediction result or later market outcome. Subsequent market success or
failure never changes a transition, and no prediction or trading signal is produced.

## Verification and non-goals

Tests exercise S1-S3 initialization, every published Error, the exact five-field
contract, Skill transitions, all recurrence states, contributor ordering, repeated
priority, no-error/abstention preservation, immutable aliases, input binding,
duck/subclass/spoof rejection and public construction/restoration attacks.
Separate verification explicitly enumerates and loads every tests/**/test_*.py;
baseline Training 43 and Evaluation 58 must continue to pass, with no skipped tests.

No Training, Evaluation, Learning Map or shared-contract mutation; no Study Entry,
Review implementation, Stage promotion, automatic STABLE, ordinary Evaluation
improvement/resolution, S4-S8, new Skill/Error/status, scoring, ranking, rewards,
prediction, market data, persistence/database, private learning history, API, UI,
plugin, network/LLM SDK, shared utility or general validator framework is added.
