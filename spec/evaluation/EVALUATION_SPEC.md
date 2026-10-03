# Evaluation Core MVP — Historical Diagnostic Feedback

## Ownership and approved boundary

Evaluation validates structured diagnostic feedback for exactly one already
submitted canonical `TrainingAttempt`. The user submits the Initial Analysis
before an evaluator supplies diagnostics. Evaluation never creates, edits,
revises, or overwrites that analysis, the attempt, its context, or its boundary.
The factory validates observable business invariants on the supplied original
attempt, without constructing a replacement `TrainingAttempt`. Its stored
historical Stage and KnowledgeBoundary remain the judgment authority.

The only public API is `Evaluation` and `create_evaluation`. Implementation is
in `src/price_action_learning/evaluation/core.py`; first-cycle tests are in
`tests/evaluation/test_evaluation.py`. This module uses only the standard library
and published Training types. It adds no shared abstraction or domain record.

This is a validated structured-diagnostic contract. The evaluator authors
feedback about the submitted analysis process in the context of that attempt's
`observation_task`, `primary_objective`, `target_concept_id`, Stage and historical
knowledge. Positive observations, criticism and hints must stay within this
task and the learned, Stage-allowed CORE knowledge at submission. Prose is not
automatically classified or checked against invented analysis criteria. The
factory enforces canonical structured authority and text shape; it does not
infer market facts, detect technical-analysis errors, or perform NLP.

## Process judgment and historical authority

Evaluate how the user observed and reasoned about the submitted evidence.
Later price movement, future candles, realized P/L, trade results, prediction
results and later market outcomes cannot be inputs. The operation returns no
prediction or trading signal and has no outcome, network or market-data
dependency. A lucky subsequent result does not validate a poor analysis
process; a subsequent adverse result does not invalidate a sound process.

The sole formal judgment authority is the submission-time frozen
`attempt.context.knowledge_boundary`. Current LearningState, later learned
concepts and later Learning Map revisions are never consulted. The published
Training boundary derives Stage membership internally and is bound to Learning
Map commit `65cd6969e8ccf890d6e51b07fd7436564bf70421`, path
`spec/learning_map/LEARNING_MAP_SPEC.md`, blob
`726b35db8409ea03cbec33c916db7374e6724e03`.

Evaluation requires exact published `TrainingAttempt`, `TrainingContext`,
`KnowledgeBoundary` and `LearningMapReference` types. Duck types, subclasses of
these record types, arbitrary boundary/reference substitutes, missing fields,
and constructor-invalid forged or tampered records are rejected. Boundary
collections must retain canonical immutable shapes: allowed/learned IDs as
`frozenset`, and confidence as a tuple of two-string tuples. Reference scalars,
Concept IDs, Stage and confidence strings are normalized before comparison.
Boundary and context validation recheck the complete canonical allowed CORE
boundary, learned subset, reference and context. Evaluation checks matching
Stage and all initial submission invariants directly, including UUID4, UTC
timestamp, initial revision and submitted status. It consumes the supplied
attempt and its own stored historical boundary after these checks.

Training now owns the approved factory-only original-submission boundary:
ordinary/public `TrainingAttempt(...)`, replace, copy/deepcopy, pickle at every
protocol, reduction and restoration reject. Same-ID/time/analysis copied
fields cannot reconstruct an attempt with expanded learned knowledge or a
future-Stage context. A new legitimate factory submission after later learning
gets a fresh identity and is evaluated under its own historical boundary.
The original S1 attempt learned only `CON-S1-HIGH` still rejects `OBS-002` and
`LOC-001` in both primary and contributor channels.

Matching ID, timestamp, analysis, or internally valid fields is never proof of
original provenance. The supported threat model covers public APIs and
standard-library reconstruction; explicit low-level object allocation,
memory/reflection tampering and abuse of private internals are outside this
MVP. No registry, persistence, authority token, hidden field, fingerprint,
nonce, secret or parallel provenance store is added.

## Exactly nine immutable shared fields

The record is one frozen, slotted dataclass with exactly these fields, in this
order. It has no instance `__dict__`, hidden authority field or tenth persistent
field. `docs/CONTRACTS.md` remains the frozen shared contract.

| Field | Representation and meaning |
| --- | --- |
| `attempt_id` | Canonical base `str`; the submitted attempt's original ID. |
| `what_was_correct` | Immutable `tuple[str, ...]`, possibly empty; useful, historically permitted correct observations. |
| `primary_issue` | `str \| None`; one diagnostic explanation in prose. |
| `primary_error` | `str \| None`; at most one eligible canonical formal Error ID. |
| `contributors` | Immutable `tuple[str, ...]`; zero, one or two unique eligible formal Error IDs, preserving evaluator order and excluding the primary. |
| `hint` | `str \| None`; educational diagnostic prose for the submitted task. |
| `skill_signal` | Derived canonical base `str`; one existing S1-S3 Skill ID. |
| `evaluation_confidence` | Canonical base `str`: exactly `HIGH`, `MEDIUM` or `LOW`. |
| `abstain` | Strict `bool`; no truthy, numeric or bool-like substitutes. |

Every supplied text value must be a string with non-whitespace content.
Optional prose and primary Error accept `None`; collection members do not.
The operation preserves text content rather than trimming or rewriting it.
String subclasses are copied to independent base `str` values using the base
string operation before validation, so custom equality, hashing, `__str__` or
`strip` cannot spoof canonical authority. Non-string spoof objects are rejected.

`what_was_correct` and `contributors` accept ordered lists or tuples, including
their subclasses using base collection iteration. Bare strings, bytes,
unordered containers and malformed members are rejected. Stored collections
are copied immutable tuples; no mutable caller-owned collection or text
subclass is retained. Caller mutation after the call cannot change the record.

`primary_issue` and `hint` contain diagnostic prose, never alternate formal
Error containers. Any occurrence of an approved Error ID text token in either
field is rejected, including punctuation, combined IDs and string-subclass
inputs. Hints must not carry a second primary error, future-stage judgment,
forecast or trading signal. This narrow protocol check is not an NLP classifier.

## Formal Error eligibility and cardinality

For every requested primary Error and every contributor, require all of:

1. The ID is one of the 19 approved Error IDs in the frozen Learning Map.
2. Its canonical Error Stage is no later than the submission Stage.
3. At least one canonically mapped supporting Concept ID is simultaneously
   learned at submission, in that Stage's canonical allowed boundary, and CORE.

Otherwise reject the requested formal Error. Stage allowance alone never means
the supporting knowledge was learned. Unavailable supporting knowledge can
instead lead the evaluator to abstain without manufacturing formal errors.

The complete Stage ceilings are:

| Error Stage | Canonical Error IDs | Permitted attempt Stages, subject to learned CORE support |
| --- | --- | --- |
| S1 | `OBS-001`, `OBS-002`, `OBS-004`, `STR-001`, `STR-002`, `STR-006`, `STR-007` | S1, S2, S3 |
| S2 | `STR-003`, `STR-004`, `STR-005`, `REA-002`, `REA-003`, `REA-005` | S2, S3 |
| S3 | `LOC-001`, `LOC-002`, `LOC-003`, `LOC-004`, `LOC-005`, `LOC-006` | S3 |

Runtime compatibility data comprises only immutable Error-to-Stage,
Error-to-Concept-IDs, Error-to-Skill links and Stage-to-primary-Skill links from
that frozen specification. It copies no Concept definitions or teaching
content. The public factory accepts no mapping or learned-boundary override.

`primary_error` is one string or `None`, never an error list. Contributors are
limited to two, must be unique after normalization and cannot contain the
primary Error. Unknown IDs, multiple primary IDs, duplicate contributors,
primary duplication and larger contributor collections are rejected. No other
Error field or error-list parameter exists.

## Confidence, abstention and skills

When `abstain=True`, `primary_error` must be `None` and `contributors` empty.
Useful positive observations and permitted prose may remain. `LOW` confidence
requires abstention. `HIGH` and `MEDIUM` may also abstain for insufficient or
ambiguous evidence or unavailable permitted knowledge. A correct analysis can
use `abstain=False`, no primary Error and no contributors; no error does not
automatically mean abstention.

Evaluation confidence expresses certainty about this particular diagnostic
assessment. It is separate from Learning Map Knowledge Confidence and is not
a probability of subsequent market movement, score, rank or reward.

Derive `skill_signal` internally in this precedence order:

1. If there is a primary Error, use its canonical related Skill.
2. Otherwise, if there are contributors, use the first contributor's Skill.
3. Otherwise, use the attempt Stage's primary Skill:
   S1 → `SKL-S1-MARKET-STATE`, S2 → `SKL-S2-STRUCTURE-MOVEMENT`,
   S3 → `SKL-S3-MARKET-LOCATION`.

Earlier-stage eligible Errors retain their own related Skill. No caller can
override the Skill, Stage, target, objective, observation task, boundary,
mapping or future outcome. No LearningState transition occurs.

## Public construction hardening

The dataclass has initialization disabled and public `__new__` always raises
`TypeError`. `Evaluation()` with zero arguments, nine arguments, nine keyword
fields, malformed fields or a proposed validation/authority token cannot create
a record. `dataclasses.replace` reconstruction also fails through this blocked
constructor. There is no public unchecked builder or caller token.

`create_evaluation` is the only supported creation path. It first independently
validates the supplied original Training submission, copies and validates diagnostic text,
checks every Error's historical eligibility, cardinality, strict abstention and
confidence rules, and derives the Skill. Only after all validation succeeds does
it privately allocate via `object.__new__(Evaluation)` and assign the nine
validated immutable values. No input record, context, boundary or Initial
Analysis is retained as mutable authority or changed during this process.

## First-cycle verification and non-goals

The numbered PRE cases 01-33 execute in the dedicated Evaluation test file;
cases 34 and 35 require independent execution of all current Training
tests and every current project test file. Tests cover constructor bypasses,
exact fields/slots, forged canonical inputs, equality spoofs, nested aliases,
all Stage ceilings, historical learning, 0/1/2 contributor paths, every Skill
branch, abstention/confidence, prose protocol bypasses and forbidden overrides.
Mapping tests independently read the unchanged frozen Learning Map and exercise
each Error against every allowed supporting or non-supporting learned Concept.
Full-suite verification enumerates `test_*.py` files and executes each explicitly;
root discovery that silently skips non-package directories is not sufficient.

The submission-provenance fix is approved across exactly the Training and
Evaluation specs, their core runtime files and their two test files. It
preserves EVAL-POST-001: public Evaluation construction/replace remain blocked,
restoration and reduction reject, all pickle protocols reject, and no mutable
restoration alias can change the nine-field record.

This MVP does not modify Learning Map, shared contracts, public exports,
LearningState, Review, Study Entry, revision flow, S4-S8, new Concepts/Errors/
Skills, screenshot interpretation, TradingView, market data, prediction,
signals, scoring, ranking, rewards, gamification, persistence, database, API
server, Web UI, plugin, LLM SDK, prompt framework, shared helpers or a generalized
validator. The complete candidate also retains the prior Evaluation package
exports and removal of its spec `.gitkeep`; the effective fix changes only
the six approved Training/Evaluation paths.
