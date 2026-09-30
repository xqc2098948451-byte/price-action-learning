# Learning Map v1 — S1–S3

## 1. Purpose and Scope

The Learning Map is the minimum domain contract for later Training, Evaluation, and Learning State work. It governs what may be trained and judged at the current Stage. The MVP sequence is **S1 Market State → S2 Structure Movement → S3 Market Location**: **State → Movement → Location**. This specification defines learning boundaries and mappings, not runtime behavior or a complete technical-analysis knowledge base.

## 2. Core Invariants

1. Stage defines the knowledge boundary. Learning Map governs what may be trained or judged within it.
2. Formal error judgment of a TrainingAttempt requires a concept that is `CORE`, allowed by that attempt's own Stage, and learned by the user when its analysis was submitted. Stage or Concept knowledge learned only after that submission must not be used to retroactively mark or penalize that attempt.
3. `CONTEXTUAL` knowledge may explain context but cannot independently justify a formal error. `CONTESTED` knowledge is excluded from core training by default.
4. Knowledge Confidence describes a concept's teaching and judgment authority; Evaluation Confidence describes confidence in a particular evaluation. They are separate.
5. Reuse an existing concept before adding one. The Learning Map is not a complete technical-analysis knowledge base.
6. S4–S8 are outside the MVP and have no implementation contract here.

## 3. Minimal Record Shapes

These are conceptual fields, not storage schemas. IDs below are stable within this specification.

| Record | Minimum fields |
| --- | --- |
| Stage | `stage_id`, `name`, `objective`, `primary_skill`, `allowed_concepts`, `initial_training_concepts`, `core_errors`, `training_cases`, `principles` |
| Skill | `skill_id`, `name`, `stage`, `objective`, `related_errors` |
| Concept | `concept_id`, `name`, `canonical_definition`, `stage`, `prerequisites`, `boundary`, `confidence`, `related_skill`, `related_errors`, `allowed_use` |
| Error | `error_id`, `stage`, `related_skill`, `related_concepts` |

Detailed error detection criteria belong to a future Evaluation specification. These records do not define scoring, severity, or detection logic.

## 4. Knowledge Confidence

The complete set is exactly `CORE`, `CONTEXTUAL`, and `CONTESTED`.

| Value | Permitted use |
| --- | --- |
| `CORE` | May be taught and trained; may support formal judgment only when Stage-allowed and learned. |
| `CONTEXTUAL` | May explain context; cannot independently mark an analysis wrong. |
| `CONTESTED` | Excluded from core training by default. |

All approved S1–S3 concepts in this document are `CORE`. The other two values define the boundary for future knowledge; they do not add concepts here.

## 5. Knowledge Boundary

Boundaries are cumulative, but training is selective. `allowed_concepts` is the ceiling for a Stage; `initial_training_concepts` is the smaller set targeted first. S1 may formally use learned S1 concepts. S2 may use learned S1 concepts plus learned S2 concepts. S3 may use learned S1/S2 concepts plus learned S3 concepts. Every formal judgment still passes the rule in Section 2. Future-stage and unapproved-system concepts remain forbidden at S1–S3.

## 6. Stage Map

Concept sets named below refer to the exact Concept IDs in Section 8. `S1 set`, `S2 set`, and `S3 set` mean the concepts whose `stage` field is S1, S2, and S3 respectively. Cumulative allowance does not imply simultaneous training.

### S1 — Market State

- `stage_id`: `S1`; `name`: Market State; `objective`: Determine what the market is doing before prediction; `primary_skill`: `SKL-S1-MARKET-STATE`.
- `allowed_concepts`: S1 set; `initial_training_concepts`: S1 set.
- `core_errors`: `OBS-001`, `OBS-002`, `OBS-004`, `STR-001`, `STR-002`, `STR-006`, `STR-007`.
- `training_cases`: clear uptrend; clear downtrend; clear range; trend with noise; genuinely ambiguous.
- `principles`: structure before prediction; observable facts before interpretation; uncertainty is valid when evidence is insufficient.

### S2 — Structure Movement

- `stage_id`: `S2`; `name`: Structure Movement; `objective`: Distinguish impulse and pullback, then judge whether existing structure is maintained, weakened, damaged, or changed; `primary_skill`: `SKL-S2-STRUCTURE-MOVEMENT`.
- `allowed_concepts`: S1 set plus S2 set; `initial_training_concepts`: S2 set, using learned S1 prerequisites as needed.
- `core_errors`: `STR-003`, `STR-004`, `STR-005`, `REA-002`, `REA-003`, `REA-005`.
- `training_cases`: clear trend pullback; deep pullback with intact structure; freshly damaged structure; structural damage followed by recovery; real structural change; ambiguous boundary case.
- `principles`: contrary movement does not automatically mean trend reversal; destruction of the original trend does not establish a new trend; do not overcorrect by refusing to accept a real reversal.

### S3 — Market Location

- `stage_id`: `S3`; `name`: Market Location; `objective`: Locate current price relative to genuinely relevant structural locations without proliferating arbitrary levels; `primary_skill`: `SKL-S3-MARKET-LOCATION`.
- `allowed_concepts`: S1 set plus S2 set plus S3 set; `initial_training_concepts`: `CON-S3-PREVIOUS-SIGNIFICANT-HIGH`, `CON-S3-PREVIOUS-SIGNIFICANT-LOW`, `CON-S3-RANGE-HIGH`, `CON-S3-RANGE-LOW` only. Earlier concepts require prior learning; other S3 concepts are supporting concepts, not initial training targets.
- `core_errors`: `LOC-001`, `LOC-002`, `LOC-003`, `LOC-004`, `LOC-005`, `LOC-006`.
- `training_cases`: locating current price relative to a previous significant high or low and an established range high or low, with competing less relevant levels.
- `principles`: use few but relevant locations; an important location does not imply a guaranteed reversal.

## 7. Skill Map

Exactly one primary skill belongs to each MVP Stage. `related_errors` references the IDs in Section 9.

| `skill_id` | `name` | `stage` | `objective` | `related_errors` |
| --- | --- | --- | --- | --- |
| `SKL-S1-MARKET-STATE` | Market State Reading | S1 | Observe structural facts and classify market state before prediction. | All S1 core errors |
| `SKL-S2-STRUCTURE-MOVEMENT` | Structure Movement Reading | S2 | Distinguish impulse/pullback and judge whether existing structure is maintained, weakened, damaged, or changed. | All S2 core errors |
| `SKL-S3-MARKET-LOCATION` | Market Location Reading | S3 | Locate current price relative to genuinely relevant structural locations without proliferating arbitrary levels. | All S3 core errors |

## 8. Concept Map

Every row is one Concept record. In each subsection, the heading supplies `stage`, `confidence = CORE`, and `related_skill` for all its rows. `Initial` in `allowed_use` means an initial training target; `Supporting` means Stage-allowed context that is not an initial training target. Either use may support formal judgment only after the concept is learned and the current Stage allows it. A prerequisite describes learning order, not an additional concept. `boundary` limits the concept's use; definitions remain observational and non-predictive.

### S1 concepts — `stage = S1`; `related_skill = SKL-S1-MARKET-STATE`

| `concept_id` | `name` | `canonical_definition` | `prerequisites` | `boundary` | `related_errors` | `allowed_use` |
| --- | --- | --- | --- | --- | --- | --- |
| `CON-S1-HIGH` | High | Greatest observed price in the chosen bar or interval. | None | State the interval; not automatically a structural turn. | `OBS-001` | Initial |
| `CON-S1-LOW` | Low | Least observed price in the chosen bar or interval. | None | State the interval; not automatically a structural turn. | `OBS-001` | Initial |
| `CON-S1-SWING-HIGH` | Swing High | Observed local turning high in a price sequence. | High | Requires a visible turn; not every bar high qualifies. | `OBS-001`, `STR-001` | Initial |
| `CON-S1-SWING-LOW` | Swing Low | Observed local turning low in a price sequence. | Low | Requires a visible turn; not every bar low qualifies. | `OBS-001`, `STR-001` | Initial |
| `CON-S1-HH` | HH | Swing high above the preceding comparable swing high. | Swing High | Comparison must use comparable structural swings. | `STR-001`, `STR-002` | Initial |
| `CON-S1-HL` | HL | Swing low above the preceding comparable swing low. | Swing Low | Comparison must use comparable structural swings. | `STR-001`, `STR-002` | Initial |
| `CON-S1-LH` | LH | Swing high below the preceding comparable swing high. | Swing High | Comparison must use comparable structural swings. | `STR-001`, `STR-002` | Initial |
| `CON-S1-LL` | LL | Swing low below the preceding comparable swing low. | Swing Low | Comparison must use comparable structural swings. | `STR-001`, `STR-002` | Initial |
| `CON-S1-UPTREND` | Uptrend | Observed sequence of higher swing highs and higher swing lows. | HH, HL | One higher high alone does not establish it. | `STR-002`, `STR-006` | Initial |
| `CON-S1-DOWNTREND` | Downtrend | Observed sequence of lower swing highs and lower swing lows. | LH, LL | One lower low alone does not establish it. | `STR-002`, `STR-006` | Initial |
| `CON-S1-RANGE` | Range | Observed movement between recurring upper and lower boundaries without a sustained directional swing sequence. | Swing High, Swing Low | A single pause does not establish a range. | `STR-002`, `STR-007` | Initial |
| `CON-S1-UNCERTAIN` | Uncertain | State used when observed structure is insufficient or conflicting. | Fact vs Interpretation | Expresses evidence limits, not a prediction. | `OBS-004`, `STR-007` | Initial |
| `CON-S1-FACT-VS-INTERPRETATION` | Fact vs Interpretation | Separation of directly observed price facts from an inference about those facts. | High, Low | An interpretation must be identified as such. | `OBS-002`, `OBS-004` | Initial |

### S2 concepts — `stage = S2`; `related_skill = SKL-S2-STRUCTURE-MOVEMENT`

| `concept_id` | `name` | `canonical_definition` | `prerequisites` | `boundary` | `related_errors` | `allowed_use` |
| --- | --- | --- | --- | --- | --- | --- |
| `CON-S2-IMPULSE` | Impulse | Directional leg that extends away from a preceding structural turn with comparatively limited counter-movement. | Swing High, Swing Low | A leg alone does not establish a trend. | `STR-003`, `REA-002` | Initial |
| `CON-S2-PULLBACK` | Pullback | Movement contrary to a preceding directional leg within the structure being assessed. | Impulse, Uptrend/Downtrend | Contrary movement alone does not prove reversal. | `STR-003`, `STR-004`, `REA-002` | Initial |
| `CON-S2-STRUCTURE-MAINTAINED` | Structure Maintained | Existing reference swing pattern remains intact after new movement. | HH/HL or LH/LL, Pullback | Does not guarantee continuation. | `STR-004`, `REA-003` | Initial |
| `CON-S2-STRUCTURE-WEAKENED` | Structure Weakened | Adverse movement or failed extension reduces clarity while the reference structure remains intact. | Structure Maintained | Weakened is not yet damaged or changed. | `STR-004`, `REA-003` | Initial |
| `CON-S2-STRUCTURE-DAMAGED` | Structure Damaged | A reference structural swing is breached, so the prior pattern no longer remains intact. | Structure Maintained | Damage alone does not establish an opposing trend. | `STR-005`, `REA-003` | Initial |
| `CON-S2-STRUCTURE-CHANGED` | Structure Changed | An opposing structural swing sequence is observed after the prior structure ceases to hold. | Structure Damaged, HH/HL or LH/LL | Requires observed opposing structure, not an assumed reversal. | `STR-005`, `REA-005` | Initial |

### S3 concepts — `stage = S3`; `related_skill = SKL-S3-MARKET-LOCATION`

| `concept_id` | `name` | `canonical_definition` | `prerequisites` | `boundary` | `related_errors` | `allowed_use` |
| --- | --- | --- | --- | --- | --- | --- |
| `CON-S3-PREVIOUS-SIGNIFICANT-HIGH` | Previous Significant High | Earlier high with a visible role in the current structural reading. | Swing High, Uptrend/Downtrend/Range | Significance needs a structural reason, not recency alone. | `LOC-001`, `LOC-002` | Initial |
| `CON-S3-PREVIOUS-SIGNIFICANT-LOW` | Previous Significant Low | Earlier low with a visible role in the current structural reading. | Swing Low, Uptrend/Downtrend/Range | Significance needs a structural reason, not recency alone. | `LOC-001`, `LOC-002` | Initial |
| `CON-S3-MAJOR-SWING-HIGH` | Major Swing High | Swing high anchoring the broader visible structure. | Swing High | Describes structural scale, not every previous significant high. | `LOC-002`, `LOC-003` | Supporting |
| `CON-S3-MAJOR-SWING-LOW` | Major Swing Low | Swing low anchoring the broader visible structure. | Swing Low | Describes structural scale, not every previous significant low. | `LOC-002`, `LOC-003` | Supporting |
| `CON-S3-RANGE-HIGH` | Range High | Observed upper boundary of an established range. | Range | Not an arbitrary isolated high. | `LOC-001`, `LOC-004` | Initial |
| `CON-S3-RANGE-LOW` | Range Low | Observed lower boundary of an established range. | Range | Not an arbitrary isolated low. | `LOC-001`, `LOC-004` | Initial |
| `CON-S3-STRUCTURAL-AREA` | Structural Area | Bounded price area around a relevant structural location when observations do not support one exact price. | Previous Significant High/Low or Range High/Low | A broad arbitrary zone is not a location. | `LOC-003`, `LOC-005` | Supporting |
| `CON-S3-CURRENT-LOCATION` | Current Location | Observed position of current price relative to selected relevant structure. | Previous Significant High/Low or Range High/Low | Location does not predict the next move. | `LOC-004`, `LOC-006` | Supporting |
| `CON-S3-RELEVANT-VS-LESS-RELEVANT` | Relevant vs Less Relevant | Comparison of candidate locations by their visible role in the current structure. | Current Location | Prefer a few justified locations; no arbitrary level collection. | `LOC-002`, `LOC-005`, `LOC-006` | Supporting |

Names joined by `/` in prerequisites denote the existing named concepts on either side, not new concepts or synonyms.

## 9. Error Map

Each approved ID appears once below. The links identify relevant concepts only; they do not define what detects an error. All linked concepts are Concept IDs from Section 8.

| `error_id` | `stage` | `related_skill` | `related_concepts` |
| --- | --- | --- | --- |
| `OBS-001` | S1 | `SKL-S1-MARKET-STATE` | `CON-S1-HIGH`, `CON-S1-LOW`, `CON-S1-SWING-HIGH`, `CON-S1-SWING-LOW` |
| `OBS-002` | S1 | `SKL-S1-MARKET-STATE` | `CON-S1-FACT-VS-INTERPRETATION` |
| `OBS-004` | S1 | `SKL-S1-MARKET-STATE` | `CON-S1-FACT-VS-INTERPRETATION`, `CON-S1-UNCERTAIN` |
| `STR-001` | S1 | `SKL-S1-MARKET-STATE` | `CON-S1-SWING-HIGH`, `CON-S1-SWING-LOW`, `CON-S1-HH`, `CON-S1-HL`, `CON-S1-LH`, `CON-S1-LL` |
| `STR-002` | S1 | `SKL-S1-MARKET-STATE` | `CON-S1-HH`, `CON-S1-HL`, `CON-S1-LH`, `CON-S1-LL`, `CON-S1-UPTREND`, `CON-S1-DOWNTREND`, `CON-S1-RANGE` |
| `STR-006` | S1 | `SKL-S1-MARKET-STATE` | `CON-S1-UPTREND`, `CON-S1-DOWNTREND` |
| `STR-007` | S1 | `SKL-S1-MARKET-STATE` | `CON-S1-RANGE`, `CON-S1-UNCERTAIN` |
| `STR-003` | S2 | `SKL-S2-STRUCTURE-MOVEMENT` | `CON-S2-IMPULSE`, `CON-S2-PULLBACK` |
| `STR-004` | S2 | `SKL-S2-STRUCTURE-MOVEMENT` | `CON-S2-PULLBACK`, `CON-S2-STRUCTURE-MAINTAINED`, `CON-S2-STRUCTURE-WEAKENED` |
| `STR-005` | S2 | `SKL-S2-STRUCTURE-MOVEMENT` | `CON-S2-STRUCTURE-DAMAGED`, `CON-S2-STRUCTURE-CHANGED` |
| `REA-002` | S2 | `SKL-S2-STRUCTURE-MOVEMENT` | `CON-S2-IMPULSE`, `CON-S2-PULLBACK` |
| `REA-003` | S2 | `SKL-S2-STRUCTURE-MOVEMENT` | `CON-S2-STRUCTURE-MAINTAINED`, `CON-S2-STRUCTURE-WEAKENED`, `CON-S2-STRUCTURE-DAMAGED` |
| `REA-005` | S2 | `SKL-S2-STRUCTURE-MOVEMENT` | `CON-S2-STRUCTURE-CHANGED` |
| `LOC-001` | S3 | `SKL-S3-MARKET-LOCATION` | `CON-S3-PREVIOUS-SIGNIFICANT-HIGH`, `CON-S3-PREVIOUS-SIGNIFICANT-LOW`, `CON-S3-RANGE-HIGH`, `CON-S3-RANGE-LOW` |
| `LOC-002` | S3 | `SKL-S3-MARKET-LOCATION` | `CON-S3-PREVIOUS-SIGNIFICANT-HIGH`, `CON-S3-PREVIOUS-SIGNIFICANT-LOW`, `CON-S3-MAJOR-SWING-HIGH`, `CON-S3-MAJOR-SWING-LOW`, `CON-S3-RELEVANT-VS-LESS-RELEVANT` |
| `LOC-003` | S3 | `SKL-S3-MARKET-LOCATION` | `CON-S3-MAJOR-SWING-HIGH`, `CON-S3-MAJOR-SWING-LOW`, `CON-S3-STRUCTURAL-AREA` |
| `LOC-004` | S3 | `SKL-S3-MARKET-LOCATION` | `CON-S3-RANGE-HIGH`, `CON-S3-RANGE-LOW`, `CON-S3-CURRENT-LOCATION` |
| `LOC-005` | S3 | `SKL-S3-MARKET-LOCATION` | `CON-S3-STRUCTURAL-AREA`, `CON-S3-RELEVANT-VS-LESS-RELEVANT` |
| `LOC-006` | S3 | `SKL-S3-MARKET-LOCATION` | `CON-S3-CURRENT-LOCATION`, `CON-S3-RELEVANT-VS-LESS-RELEVANT` |

## 10. Future Concept Expansion Boundary

Reuse an existing concept first. If a distinction is missing, add a relation or clarify a boundary before proposing a new concept. A new concept is warranted only when the current learning loop cannot proceed without it, and it requires explicit governed approval before joining the official Learning Map. No candidate lifecycle, storage format, or automation is defined here.

## 11. Explicit Non-Goals

This specification does not provide S4–S8 contracts, indicators, Elliott Wave, harmonic patterns, ICT, SMC, FVG, trading signals, market prediction, automatic trading, or a full risk-management system. It does not define scoring, ranking, gamification, a database, knowledge graph engine, Web UI, API server, or plugin implementation. Training, Evaluation, Learning State, Review, Study Entry, and Candidate Concept Expansion implementations are outside this Work Unit.
