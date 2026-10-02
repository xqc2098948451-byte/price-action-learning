"""Submission-time Training records for the frozen S1-S3 Learning Map."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4


# Compatibility membership only. Definitions and teaching rules remain in the
# immutable Learning Map specification identified by _LEARNING_MAP_REFERENCE.
_STAGE_CONCEPT_IDS = {
    "S1": (
        "CON-S1-HIGH", "CON-S1-LOW", "CON-S1-SWING-HIGH", "CON-S1-SWING-LOW",
        "CON-S1-HH", "CON-S1-HL", "CON-S1-LH", "CON-S1-LL",
        "CON-S1-UPTREND", "CON-S1-DOWNTREND", "CON-S1-RANGE",
        "CON-S1-UNCERTAIN", "CON-S1-FACT-VS-INTERPRETATION",
    ),
    "S2": (
        "CON-S2-IMPULSE", "CON-S2-PULLBACK", "CON-S2-STRUCTURE-MAINTAINED",
        "CON-S2-STRUCTURE-WEAKENED", "CON-S2-STRUCTURE-DAMAGED",
        "CON-S2-STRUCTURE-CHANGED",
    ),
    "S3": (
        "CON-S3-PREVIOUS-SIGNIFICANT-HIGH",
        "CON-S3-PREVIOUS-SIGNIFICANT-LOW", "CON-S3-MAJOR-SWING-HIGH",
        "CON-S3-MAJOR-SWING-LOW", "CON-S3-RANGE-HIGH", "CON-S3-RANGE-LOW",
        "CON-S3-STRUCTURAL-AREA", "CON-S3-CURRENT-LOCATION",
        "CON-S3-RELEVANT-VS-LESS-RELEVANT",
    ),
}


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    text = str.__str__(value)
    if not text.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _allowed_for_stage(stage: str) -> frozenset[str]:
    if not isinstance(stage, str) or stage not in _STAGE_CONCEPT_IDS:
        raise ValueError("stage must be S1, S2, or S3")
    allowed = set()
    for current_stage, concepts in _STAGE_CONCEPT_IDS.items():
        allowed.update(concepts)
        if current_stage == stage:
            break
    return frozenset(allowed)


@dataclass(frozen=True)
class LearningMapReference:
    commit: str
    path: str
    blob: str


def _canonical_learning_map_reference() -> LearningMapReference:
    return LearningMapReference(
        commit="65cd6969e8ccf890d6e51b07fd7436564bf70421",
        path="spec/learning_map/LEARNING_MAP_SPEC.md",
        blob="726b35db8409ea03cbec33c916db7374e6724e03",
    )


_LEARNING_MAP_REFERENCE = _canonical_learning_map_reference()


@dataclass(frozen=True)
class KnowledgeBoundary:
    stage: str
    allowed_concept_ids: frozenset[str]
    learned_concept_ids: frozenset[str]
    concept_confidence: tuple[tuple[str, str], ...]
    learning_map_reference: LearningMapReference

    def __post_init__(self) -> None:
        if not isinstance(self.stage, str):
            raise ValueError("stage must be S1, S2, or S3")
        stage = str.__str__(self.stage)
        canonical = _allowed_for_stage(stage)
        try:
            allowed = frozenset(str.__str__(concept) for concept in self.allowed_concept_ids)
            learned = frozenset(str.__str__(concept) for concept in self.learned_concept_ids)
        except (TypeError, AttributeError) as exc:
            raise ValueError("Concept IDs must be strings") from exc
        confidence = tuple(tuple(pair) for pair in self.concept_confidence)
        expected_confidence = tuple((concept, "CORE") for concept in sorted(canonical))
        if allowed != canonical:
            raise ValueError("allowed_concept_ids must be the canonical Stage boundary")
        if not learned <= canonical:
            raise ValueError("learned_concept_ids must belong to the Stage boundary")
        if confidence != expected_confidence:
            raise ValueError("concept_confidence must match the canonical CORE boundary")
        if (type(self.learning_map_reference) is not LearningMapReference
                or self.learning_map_reference != _LEARNING_MAP_REFERENCE):
            raise ValueError("learning_map_reference must identify the canonical Learning Map")
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "allowed_concept_ids", canonical)
        object.__setattr__(self, "learned_concept_ids", learned)
        object.__setattr__(self, "concept_confidence", expected_confidence)
        object.__setattr__(self, "learning_map_reference", _canonical_learning_map_reference())


@dataclass(frozen=True)
class TrainingContext:
    market_scenario: str
    observation_task: str
    primary_objective: str
    target_concept_id: str
    training_mode: str
    focus_error_id: str | None
    knowledge_boundary: KnowledgeBoundary

    def __post_init__(self) -> None:
        for field_name in ("market_scenario", "observation_task", "primary_objective",
                           "target_concept_id"):
            text = _required_text(getattr(self, field_name), field_name)
            object.__setattr__(self, field_name, text)
        if not isinstance(self.training_mode, str):
            raise ValueError("training_mode must be FORMAL or FOCUSED")
        object.__setattr__(self, "training_mode", str.__str__(self.training_mode))
        if self.training_mode not in {"FORMAL", "FOCUSED"}:
            raise ValueError("training_mode must be FORMAL or FOCUSED")
        if self.training_mode == "FOCUSED":
            focus_error_id = _required_text(self.focus_error_id, "focus_error_id")
            object.__setattr__(self, "focus_error_id", focus_error_id)
        elif self.focus_error_id is not None:
            focus_error_id = _required_text(self.focus_error_id, "focus_error_id")
            object.__setattr__(self, "focus_error_id", focus_error_id)
        source = self.knowledge_boundary
        try:
            boundary = KnowledgeBoundary(
                stage=source.stage,
                allowed_concept_ids=source.allowed_concept_ids,
                learned_concept_ids=source.learned_concept_ids,
                concept_confidence=source.concept_confidence,
                learning_map_reference=source.learning_map_reference,
            )
        except (AttributeError, TypeError) as exc:
            raise ValueError("knowledge_boundary must be a canonical KnowledgeBoundary") from exc
        if self.target_concept_id not in boundary.allowed_concept_ids:
            raise ValueError("target_concept_id must belong to the Stage boundary")
        object.__setattr__(self, "knowledge_boundary", boundary)


@dataclass(frozen=True)
class TrainingAttempt:
    id: str
    created_at: datetime
    stage: str
    image_reference: None
    user_analysis: str
    user_confidence: str | int | float | None
    revision: None
    status: str
    context: TrainingContext

    def __post_init__(self) -> None:
        if type(self.id) is not str:
            raise ValueError("id must be a canonical UUID4 string")
        try:
            parsed_id = UUID(self.id)
        except ValueError as exc:
            raise ValueError("id must be a canonical UUID4 string") from exc
        if parsed_id.version != 4 or str(parsed_id) != self.id:
            raise ValueError("id must be a canonical UUID4 string")
        if type(self.created_at) is not datetime or self.created_at.tzinfo is not timezone.utc:
            raise ValueError("created_at must be a UTC submission timestamp")
        if self.image_reference is not None:
            raise ValueError("image_reference must be None")
        if self.revision is not None:
            raise ValueError("revision must be None for initial submission")
        if type(self.status) is not str or self.status != "SUBMITTED":
            raise ValueError("status must be SUBMITTED for initial submission")
        if not isinstance(self.user_analysis, str):
            raise ValueError("user_analysis must be a non-empty string")
        analysis = _required_text(str.__str__(self.user_analysis), "user_analysis")
        if self.user_confidence is not None and (
            isinstance(self.user_confidence, bool)
            or not isinstance(self.user_confidence, (str, int, float))
        ):
            raise ValueError("user_confidence must be an immutable scalar or None")
        confidence = self.user_confidence
        if isinstance(confidence, str):
            confidence = str.__str__(confidence)
        elif isinstance(confidence, int):
            confidence = int.__int__(confidence)
        elif isinstance(confidence, float):
            confidence = float.__float__(confidence)
        if type(self.context) is not TrainingContext:
            raise ValueError("context must be a canonical TrainingContext")
        source = self.context
        context = TrainingContext(
            market_scenario=source.market_scenario,
            observation_task=source.observation_task,
            primary_objective=source.primary_objective,
            target_concept_id=source.target_concept_id,
            training_mode=source.training_mode,
            focus_error_id=source.focus_error_id,
            knowledge_boundary=source.knowledge_boundary,
        )
        if not isinstance(self.stage, str) or str.__str__(self.stage) != context.knowledge_boundary.stage:
            raise ValueError("stage must match context.knowledge_boundary.stage")
        object.__setattr__(self, "stage", context.knowledge_boundary.stage)
        object.__setattr__(self, "user_analysis", analysis)
        object.__setattr__(self, "user_confidence", confidence)
        object.__setattr__(self, "context", context)


def create_training_attempt(
    *,
    stage: str,
    market_scenario: str,
    observation_task: str,
    primary_objective: str,
    target_concept_id: str,
    training_mode: str,
    learned_concept_ids,
    user_analysis: str,
    user_confidence: str | int | float | None = None,
    focus_error_id: str | None = None,
) -> TrainingAttempt:
    """Record one Formal or Focused user submission without evaluating it."""
    allowed = _allowed_for_stage(stage)
    _required_text(user_analysis, "user_analysis")
    if user_confidence is not None and (
        isinstance(user_confidence, bool)
        or not isinstance(user_confidence, (str, int, float))
    ):
        raise ValueError("user_confidence must be an immutable scalar or None")
    if isinstance(learned_concept_ids, (str, bytes)):
        raise ValueError("learned_concept_ids must be a collection of Concept IDs")
    try:
        learned = frozenset(learned_concept_ids)
    except (TypeError, ValueError) as exc:
        raise ValueError("learned_concept_ids must be a collection of Concept IDs") from exc
    if not learned <= allowed:
        raise ValueError("learned_concept_ids must belong to the Stage boundary")
    boundary = KnowledgeBoundary(
        stage=stage,
        allowed_concept_ids=allowed,
        learned_concept_ids=learned,
        concept_confidence=tuple((concept, "CORE") for concept in sorted(allowed)),
        learning_map_reference=_LEARNING_MAP_REFERENCE,
    )
    context = TrainingContext(
        market_scenario=market_scenario,
        observation_task=observation_task,
        primary_objective=primary_objective,
        target_concept_id=target_concept_id,
        training_mode=training_mode,
        focus_error_id=focus_error_id,
        knowledge_boundary=boundary,
    )
    return TrainingAttempt(
        id=str(uuid4()),
        created_at=datetime.now(timezone.utc),
        stage=stage,
        image_reference=None,
        user_analysis=user_analysis,
        user_confidence=user_confidence,
        revision=None,
        status="SUBMITTED",
        context=context,
    )
