"""Validated diagnostic feedback for one historical Training submission."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from price_action_learning.training import (
    KnowledgeBoundary,
    LearningMapReference,
    TrainingAttempt,
    TrainingContext,
)


# Compatibility links only, from Learning Map commit
# 65cd6969e8ccf890d6e51b07fd7436564bf70421, blob
# 726b35db8409ea03cbec33c916db7374e6724e03. No definitions or teaching content.
# Each immutable row is Error -> (Stage, Concept IDs, related Skill).
_ERROR_COMPATIBILITY = (
    ("OBS-001", "S1", ("CON-S1-HIGH", "CON-S1-LOW", "CON-S1-SWING-HIGH",
                       "CON-S1-SWING-LOW"), "SKL-S1-MARKET-STATE"),
    ("OBS-002", "S1", ("CON-S1-FACT-VS-INTERPRETATION",), "SKL-S1-MARKET-STATE"),
    ("OBS-004", "S1", ("CON-S1-FACT-VS-INTERPRETATION", "CON-S1-UNCERTAIN"),
     "SKL-S1-MARKET-STATE"),
    ("STR-001", "S1", ("CON-S1-SWING-HIGH", "CON-S1-SWING-LOW", "CON-S1-HH",
                       "CON-S1-HL", "CON-S1-LH", "CON-S1-LL"), "SKL-S1-MARKET-STATE"),
    ("STR-002", "S1", ("CON-S1-HH", "CON-S1-HL", "CON-S1-LH", "CON-S1-LL",
                       "CON-S1-UPTREND", "CON-S1-DOWNTREND", "CON-S1-RANGE"),
     "SKL-S1-MARKET-STATE"),
    ("STR-006", "S1", ("CON-S1-UPTREND", "CON-S1-DOWNTREND"), "SKL-S1-MARKET-STATE"),
    ("STR-007", "S1", ("CON-S1-RANGE", "CON-S1-UNCERTAIN"), "SKL-S1-MARKET-STATE"),
    ("STR-003", "S2", ("CON-S2-IMPULSE", "CON-S2-PULLBACK"),
     "SKL-S2-STRUCTURE-MOVEMENT"),
    ("STR-004", "S2", ("CON-S2-PULLBACK", "CON-S2-STRUCTURE-MAINTAINED",
                       "CON-S2-STRUCTURE-WEAKENED"), "SKL-S2-STRUCTURE-MOVEMENT"),
    ("STR-005", "S2", ("CON-S2-STRUCTURE-DAMAGED", "CON-S2-STRUCTURE-CHANGED"),
     "SKL-S2-STRUCTURE-MOVEMENT"),
    ("REA-002", "S2", ("CON-S2-IMPULSE", "CON-S2-PULLBACK"),
     "SKL-S2-STRUCTURE-MOVEMENT"),
    ("REA-003", "S2", ("CON-S2-STRUCTURE-MAINTAINED", "CON-S2-STRUCTURE-WEAKENED",
                       "CON-S2-STRUCTURE-DAMAGED"), "SKL-S2-STRUCTURE-MOVEMENT"),
    ("REA-005", "S2", ("CON-S2-STRUCTURE-CHANGED",), "SKL-S2-STRUCTURE-MOVEMENT"),
    ("LOC-001", "S3", ("CON-S3-PREVIOUS-SIGNIFICANT-HIGH",
                       "CON-S3-PREVIOUS-SIGNIFICANT-LOW", "CON-S3-RANGE-HIGH",
                       "CON-S3-RANGE-LOW"), "SKL-S3-MARKET-LOCATION"),
    ("LOC-002", "S3", ("CON-S3-PREVIOUS-SIGNIFICANT-HIGH",
                       "CON-S3-PREVIOUS-SIGNIFICANT-LOW", "CON-S3-MAJOR-SWING-HIGH",
                       "CON-S3-MAJOR-SWING-LOW", "CON-S3-RELEVANT-VS-LESS-RELEVANT"),
     "SKL-S3-MARKET-LOCATION"),
    ("LOC-003", "S3", ("CON-S3-MAJOR-SWING-HIGH", "CON-S3-MAJOR-SWING-LOW",
                       "CON-S3-STRUCTURAL-AREA"), "SKL-S3-MARKET-LOCATION"),
    ("LOC-004", "S3", ("CON-S3-RANGE-HIGH", "CON-S3-RANGE-LOW",
                       "CON-S3-CURRENT-LOCATION"), "SKL-S3-MARKET-LOCATION"),
    ("LOC-005", "S3", ("CON-S3-STRUCTURAL-AREA", "CON-S3-RELEVANT-VS-LESS-RELEVANT"),
     "SKL-S3-MARKET-LOCATION"),
    ("LOC-006", "S3", ("CON-S3-CURRENT-LOCATION", "CON-S3-RELEVANT-VS-LESS-RELEVANT"),
     "SKL-S3-MARKET-LOCATION"),
)
_STAGE_PRIMARY_SKILLS = (
    ("S1", "SKL-S1-MARKET-STATE"),
    ("S2", "SKL-S2-STRUCTURE-MOVEMENT"),
    ("S3", "SKL-S3-MARKET-LOCATION"),
)


@dataclass(frozen=True, slots=True, init=False)
class Evaluation:
    """Nine immutable shared fields; use create_evaluation for construction."""

    attempt_id: str
    what_was_correct: tuple[str, ...]
    primary_issue: str | None
    primary_error: str | None
    contributors: tuple[str, ...]
    hint: str | None
    skill_signal: str
    evaluation_confidence: str
    abstain: bool

    def __new__(cls, *args, **kwargs):
        raise TypeError("Evaluation must be created through create_evaluation")

    def __setstate__(self, state):
        """Reject restoration before reading state or writing validated fields."""
        raise TypeError("Evaluation state restoration is not supported")

    def __reduce__(self):
        raise TypeError("Evaluation pickle serialization is not supported")

    def __reduce_ex__(self, protocol):
        raise TypeError("Evaluation pickle serialization is not supported")


def _text(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a non-empty string")
    # Calling the base operation avoids caller __str__, strip and equality hooks.
    canonical = str.__str__(value)
    if not canonical.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return canonical


def _optional_text(value: str | None, field: str) -> str | None:
    return None if value is None else _text(value, field)


def _text_tuple(values: list[str] | tuple[str, ...], field: str) -> tuple[str, ...]:
    if isinstance(values, list):
        source = list.__iter__(values)
    elif isinstance(values, tuple):
        source = tuple.__iter__(values)
    else:
        raise ValueError(f"{field} must be an ordered list or tuple of strings")
    return tuple(_text(value, field) for value in source)


def _validated_attempt(attempt: TrainingAttempt) -> TrainingAttempt:
    """Validate business invariants and consume the supplied original submission."""
    if type(attempt) is not TrainingAttempt:
        raise ValueError("attempt must be a canonical TrainingAttempt")
    try:
        context = attempt.context
        if type(context) is not TrainingContext:
            raise ValueError("context must be a canonical TrainingContext")
        source = context.knowledge_boundary
        if type(source) is not KnowledgeBoundary:
            raise ValueError("knowledge_boundary must be a canonical KnowledgeBoundary")
        reference = source.learning_map_reference
        if type(reference) is not LearningMapReference:
            raise ValueError("reference must be a canonical LearningMapReference")
        if (type(source.allowed_concept_ids) is not frozenset
                or type(source.learned_concept_ids) is not frozenset
                or type(source.concept_confidence) is not tuple):
            raise ValueError("knowledge_boundary must retain canonical immutable collections")
        allowed = frozenset(_text(c, "allowed_concept_ids") for c in source.allowed_concept_ids)
        learned = frozenset(_text(c, "learned_concept_ids") for c in source.learned_concept_ids)
        confidence = []
        for pair in source.concept_confidence:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError("concept_confidence must contain immutable Concept/CORE pairs")
            confidence.append((_text(pair[0], "concept_confidence concept"),
                               _text(pair[1], "concept_confidence value")))
        # Normalize reference scalars and confidence pairs before the published
        # equality checks. Spoofed equality cannot manufacture canonical authority.
        boundary = KnowledgeBoundary(
            stage=_text(source.stage, "boundary stage"),
            allowed_concept_ids=allowed,
            learned_concept_ids=learned,
            concept_confidence=tuple(confidence),
            learning_map_reference=LearningMapReference(
                commit=_text(reference.commit, "reference commit"),
                path=_text(reference.path, "reference path"),
                blob=_text(reference.blob, "reference blob"),
            ),
        )
        TrainingContext(
            market_scenario=_text(context.market_scenario, "market_scenario"),
            observation_task=_text(context.observation_task, "observation_task"),
            primary_objective=_text(context.primary_objective, "primary_objective"),
            target_concept_id=_text(context.target_concept_id, "target_concept_id"),
            training_mode=_text(context.training_mode, "training_mode"),
            focus_error_id=_optional_text(context.focus_error_id, "focus_error_id"),
            knowledge_boundary=boundary,
        )
        # These are observable business checks, never proof from matching ID,
        # time or analysis. Training owns the supported construction boundary.
        if type(attempt.id) is not str:
            raise ValueError("id must be a canonical UUID4 string")
        parsed_id = UUID(attempt.id)
        if parsed_id.version != 4 or str(parsed_id) != attempt.id:
            raise ValueError("id must be a canonical UUID4 string")
        if type(attempt.created_at) is not datetime or attempt.created_at.tzinfo is not timezone.utc:
            raise ValueError("created_at must be a UTC submission timestamp")
        if attempt.image_reference is not None or attempt.revision is not None:
            raise ValueError("attempt must retain initial submission defaults")
        if type(attempt.status) is not str or attempt.status != "SUBMITTED":
            raise ValueError("status must be SUBMITTED")
        if _text(attempt.stage, "attempt stage") != boundary.stage:
            raise ValueError("stage must match the historical boundary")
        _text(attempt.user_analysis, "user_analysis")
        if attempt.user_confidence is not None and (
            isinstance(attempt.user_confidence, bool)
            or not isinstance(attempt.user_confidence, (str, int, float))
        ):
            raise ValueError("user_confidence must be an immutable scalar or None")
        return attempt
    except (AttributeError, TypeError) as exc:
        raise ValueError("attempt must satisfy the Training submission invariants") from exc


def _diagnostic_prose(value: str | None, field: str) -> str | None:
    text = _optional_text(value, field)
    if text is not None and any(error in text for error, _, _, _ in _ERROR_COMPATIBILITY):
        raise ValueError(f"{field} cannot contain approved formal Error ID tokens")
    return text


def _error_skill(error: str, boundary: KnowledgeBoundary) -> str:
    for canonical_id, stage, concepts, skill in _ERROR_COMPATIBILITY:
        if error == canonical_id:
            # Only S1-S3 have passed canonical validation, so this comparison
            # is exactly the cumulative Stage ceiling.
            if stage > _text(boundary.stage, "boundary stage"):
                raise ValueError("formal Error Stage exceeds the submission Stage")
            core = frozenset(_text(c, "Concept ID") for c, confidence in boundary.concept_confidence
                             if _text(confidence, "Concept confidence") == "CORE")
            learned = frozenset(_text(c, "learned Concept ID") for c in boundary.learned_concept_ids)
            allowed = frozenset(_text(c, "allowed Concept ID") for c in boundary.allowed_concept_ids)
            eligible = learned & allowed & core
            if not any(concept in eligible for concept in concepts):
                raise ValueError("formal Error needs a mapped historical learned allowed CORE Concept")
            return skill
    raise ValueError("formal Error ID must be approved by the frozen S1-S3 Learning Map")


def create_evaluation(
    *,
    attempt: TrainingAttempt,
    evaluation_confidence: str,
    abstain: bool,
    what_was_correct: list[str] | tuple[str, ...] = (),
    primary_issue: str | None = None,
    primary_error: str | None = None,
    contributors: list[str] | tuple[str, ...] = (),
    hint: str | None = None,
) -> Evaluation:
    """Validate evaluator-authored diagnostics for this submitted task only.

    The evaluator scopes prose to the attempt's observation task, objective,
    target, Stage and historical knowledge. This factory enforces structured
    authority and content shape; it does not classify natural language.
    """
    original = _validated_attempt(attempt)
    positives = _text_tuple(what_was_correct, "what_was_correct")
    issue = _diagnostic_prose(primary_issue, "primary_issue")
    hint_text = _diagnostic_prose(hint, "hint")
    primary = _optional_text(primary_error, "primary_error")
    contributing = _text_tuple(contributors, "contributors")
    confidence = _text(evaluation_confidence, "evaluation_confidence")
    if confidence not in ("HIGH", "MEDIUM", "LOW"):
        raise ValueError("evaluation_confidence must be HIGH, MEDIUM, or LOW")
    if type(abstain) is not bool:
        raise ValueError("abstain must be a strict bool")
    if len(contributing) > 2:
        raise ValueError("contributors may contain at most two Error IDs")
    if len(set(contributing)) != len(contributing):
        raise ValueError("contributors must be unique")
    if primary is not None and primary in contributing:
        raise ValueError("primary_error cannot also be a contributor")
    if abstain and (primary is not None or contributing):
        raise ValueError("abstention cannot contain formal errors")
    if confidence == "LOW" and not abstain:
        raise ValueError("LOW evaluation_confidence requires abstention")

    boundary = original.context.knowledge_boundary
    primary_skill = None if primary is None else _error_skill(primary, boundary)
    contributor_skills = tuple(_error_skill(error, boundary) for error in contributing)
    if primary_skill is not None:
        skill = primary_skill
    elif contributor_skills:
        skill = contributor_skills[0]
    else:
        skill = next(skill for stage, skill in _STAGE_PRIMARY_SKILLS
                     if stage == _text(original.stage, "attempt stage"))

    # All validation finishes before allocation. There is no public unchecked
    # builder, caller token, authority field, or second record type.
    result = object.__new__(Evaluation)
    values = (original.id, positives, issue, primary, contributing, hint_text,
              skill, confidence, abstain)
    for field, value in zip(Evaluation.__slots__, values):
        object.__setattr__(result, field, value)
    return result
