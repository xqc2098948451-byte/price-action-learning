# Training MVP — Formal and Focused Attempts

## Ownership and purpose

The Training module owns presentation context and the user's submitted analysis for one observation task. Its first runtime operation creates a `TrainingAttempt` for later Evaluation. Training does not diagnose, score, or change learning state. A user submits an initial analysis before any GPT diagnosis or evaluation (the user-first invariant).

The runtime behavior lives in `src/price_action_learning/training/core.py`. Both modes use the public `create_training_attempt(...)` function and return only a `TrainingAttempt`.

## One task, one target, one objective

Each creation requires non-empty `market_scenario`, `observation_task`, `primary_objective`, `target_concept_id`, and `user_analysis`. One immutable `TrainingContext` holds those fields, `training_mode`, optional `focus_error_id`, and `knowledge_boundary`. Its single `primary_objective` and `observation_task` refer to the same explicit `target_concept_id`; there is no collection of objectives or targets.

`FORMAL` and `FOCUSED` are modes of the same operation and record. `FOCUSED` requires a non-empty `focus_error_id`; `FORMAL` does not. The error ID identifies a focus only. Training makes no error judgment from it. The target concept must be allowed by the attempt's Stage, but need not already be learned: a task may introduce a permitted concept.

## Shared attempt contract

`TrainingAttempt` retains the eight shared fields from `docs/CONTRACTS.md`: `id`, `created_at`, `stage`, `image_reference`, `user_analysis`, `user_confidence`, `revision`, and `status`. The only additional field is the immutable `context`. Creation assigns a unique ID and submission timestamp, sets `image_reference = None`, `revision = None`, and `status = "SUBMITTED"`, and preserves the initial `user_analysis` without an overwrite or revision workflow. `user_confidence` is optional and, when supplied, is an immutable text or numeric scalar.

The scenario, task, objective, target, analysis, and boundary are frozen in the returned record. The operation copies caller-owned concept collections before storing them, so later caller mutation cannot rewrite the submission.

## Authoritative knowledge boundary

The authoritative Learning Map is `spec/learning_map/LEARNING_MAP_SPEC.md` at commit `65cd6969e8ccf890d6e51b07fd7436564bf70421`, blob `726b35db8409ea03cbec33c916db7374e6724e03`. Runtime compatibility data contains only Stage to Concept ID membership from that specification; it does not duplicate definitions, prerequisites, errors, or teaching content.

Supported Stages are exactly S1, S2, and S3. Cumulative allowed Concept ID counts are 13, 19, and 28, respectively. All approved S1–S3 concepts have `CORE` Knowledge Confidence. The module derives the canonical allowed set internally; callers cannot supply or expand it. `learned_concept_ids` must be a subset of the selected Stage's canonical allowed set. Unknown Stages, S4+, unknown concepts, and future-stage learned or target concepts are rejected.

Each attempt's `KnowledgeBoundary` preserves its Stage, canonical allowed Concept IDs, actually learned Concept IDs, applicable `CORE` confidence for each allowed concept, and a frozen `LearningMapReference` with the exact commit, path, and blob above. This is submission-time evidence. Later learning or a future Learning Map revision cannot alter what was available when the user submitted the analysis. A future Evaluation must use that stored boundary rather than later knowledge when considering formal judgment.

## Non-goals

This MVP has no Evaluation or LearningState output, error detection, formal judgment, score, grade, Review decision, Study Entry, revision flow, screenshot, database, persistence layer, UI, external API, TradingView integration, trading signal, risk management, automatic prediction, S4–S8 contract, or generalized snapshot engine.
