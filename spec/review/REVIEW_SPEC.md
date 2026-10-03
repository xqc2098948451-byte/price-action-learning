# Review Core

Review owns immutable targeted scheduling and conservative Review evidence for
the published S1-S3 domain contracts. It reads LearningState during scheduling,
and original TrainingAttempt and Evaluation records. It mutates no input and
retains no state or history.

## Record and public operations

The package exports only `ReviewRecord`, `schedule_reviews`, and `complete_review`.
ReviewRecord is frozen, slotted, factory-controlled, and has exactly these seven
persistent fields in order:

| Field | Representation |
| --- | --- |
| id | Canonical lower-case UUID4 base string. |
| source_attempt_id | Canonical lower-case UUID4 base string. |
| error_id | One of the published 19 canonical Error IDs, exact base string. |
| scheduled_for | Exact datetime with tzinfo identical to timezone.utc. |
| completed_at | Exact UTC datetime or None. |
| new_analysis | Nonempty immutable base string or None. |
| result | REPEATED, IMPROVING, RESOLVED, INCONCLUSIVE, or None. |

A scheduled record has all three completion fields None. A completed record has
all three present, with completed_at >= scheduled_for. Every partially completed
combination rejects. Completion returns a new record preserving the first four
fields; the original scheduled record remains unchanged.

Ordinary construction, construction from copied fields, dataclasses.replace,
copy.copy, copy.deepcopy, pickle (all protocols), reduce/reduce_ex, setstate and
standard reconstruction are unsupported and blocked. There is no __dict__, hidden
authority field, registry, token, fingerprint, serializer or database. As for the
published immutable records, malicious low-level object allocation/setattr and
private internal abuse are outside the ordinary public construction boundary.
Operations still reject malformed observable representations.

## Scheduling

`schedule_reviews(*, state, source_attempt, evaluation)` accepts only the exact
published LearningState, TrainingAttempt and Evaluation types, not subclasses or
duck types. Canonical observable fields are validated before equality checks.
Evaluation binds the supplied source attempt; state and attempt Stages match.
Evaluation must not abstain and must contain formal Errors. Formal Errors are
primary_error (if present), then contributors in stored order. current_focus must
be present in that sequence. It is the only selected Error; callers cannot override
it or infer a different Error from diagnostic prose.

The returned exact tuple contains three records in ascending day-3, day-7 and
day-30 order. Times are anchored solely to source_attempt.created_at plus those
timedeltas. IDs are fresh distinct canonical UUID4 values. All records share the
source attempt and current-focus Error and have no completion fields populated.
Scheduling does not attach IDs to reviews_due, persist records, deduplicate across
calls, run timers or start background work.

## Fresh independent completion

`complete_review(*, record, source_attempt, review_attempt, review_evaluation,
completed_at, prior_reviews=())` consumes an uncompleted canonical ReviewRecord,
the source attempt, a fresh original TrainingAttempt and its new Evaluation.
The record binds the source ID and exactly one source-anchored slot. completed_at
is an exact UTC datetime at or after scheduled_for.

The user submits independent fresh analysis before its new Evaluation is consumed.
The caller must hide the old answer and old GPT feedback during that submission.
There is no source Evaluation, old answer, old GPT issue/hint/positive feedback,
or diagnostic-prose parameter in the completion API. The source attempt is read
only for identity, time, Stage and knowledge-boundary checks; its user_analysis is
never accessed by completion. The runtime cannot prove what an external caller
showed to the user; it provides no display path for old answers or feedback.

Fresh attempt ID differs from source ID; Stages match; fresh training mode is
FOCUSED and focus_error_id equals the targeted Error. Source learned Concept IDs
must be a subset of fresh learned Concept IDs. Expansion is permitted. Original
published submission provenance is preserved: no TrainingAttempt reconstruction,
no Evaluation reconstruction, no rerunning formal Error-to-Concept eligibility.
Fresh Evaluation binds the fresh attempt. new_analysis comes exclusively from
the fresh attempt as an immutable base string. No source or predecessor answer
is compared, scored or reused to derive the result.

## Result precedence and predecessor evidence

Apply this order after completion-input validation:

1. Fresh Evaluation abstains: INCONCLUSIVE.
2. Otherwise target appears in fresh formal primary_error/contributors: REPEATED.
3. Otherwise day-3 or day-7 target absence: IMPROVING.
4. Otherwise day-30 target absence: evaluate prior_reviews as resolution evidence.

prior_reviews is **only** a resolution-evidence input for the last branch. It is
not a second global validity gate for abstention, recurrence, or earlier intervals.
No predecessor chain is required to produce INCONCLUSIVE, REPEATED, or day-3/day-7
IMPROVING. The earlier branches do not inspect it.

For non-abstaining target-absent day-30, prior_reviews must be an exact tuple with
zero, one or two members. Each supplied member must be an exact canonical completed
ReviewRecord with matching source_attempt_id and error_id, a distinct ID (also
distinct from current), an exact source-anchored day-3 or day-7 slot, and completion
at or before current completed_at. Record completion-field validity is checked;
prior new_analysis content is not analytical evidence.

| Valid supplied evidence | Outcome |
| --- | --- |
| Empty tuple | IMPROVING |
| Only completed canonical day-3, other slot absent | IMPROVING |
| Only completed canonical day-7, other slot absent | IMPROVING |
| Day-3 then day-7, both IMPROVING | RESOLVED |
| Day-3 then day-7, one or both REPEATED/INCONCLUSIVE | IMPROVING |

A two-record tuple must contain one of each slot in day-3 then day-7 order.
Malformed tuple/member, noncanonical record, wrong source/Error/slot, uncompleted
record, duplicate ID/slot, completion after current, wrong pair order, or extra
third or later member rejects. Missing qualifying evidence alone is valid and
falls back to IMPROVING. In particular, a single valid predecessor must never be
classified as invalid merely because the other slot is absent.

## Ownership and process boundaries

The 19 Error IDs remain the published Learning Map membership set. Review creates
no new IDs and implements no Error detection criteria. Evaluation owns formal
judgment. Review results describe evidence of analytical improvement, not a score,
rank, probability, prediction, market success or realized outcome. No public API
accepts future candles, later prices, P/L, trade results or market outcome.

LearningState remains the learner-state owner. Review reads its validation boundary
for scheduling and never constructs state, calls its private _build_state builder,
writes errors/focus/skills/reviews_due, decides STABLE, or promotes a Stage. No
LearningState, Training, Evaluation, Learning Map or shared-contract file changes.
A later separately governed integration WU may consume canonical ReviewRecord
evidence to update learner state. That integration and Study Entry have not begun.

No persistence, database, scheduler, UI, API, network/LLM SDK, screenshot/TradingView
integration, rewards, scoring, S4-S8, generic service/manager/repository framework
or shared utility abstraction is included.

## Validation

Review tests cover the approved 45 future requirements, including all scheduling
and result branches, canonical representation, exact-type and binding rejection,
knowledge non-regression, fresh-analysis independence, unchanged inputs, hostile
construction/restoration, and the PRE-001 partial-chain versus invalid-evidence
distinction. The explicit tests/**/test_*.py inventory also preserves all 43
LearningState, 43 Training and 58 Evaluation tests. Zero failures/errors/skips is
required. The effective candidate delta is exactly four additions and deletion
of this module's old .gitkeep; candidate publication is separately governed.
