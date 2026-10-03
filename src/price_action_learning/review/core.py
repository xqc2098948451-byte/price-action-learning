"""Source-anchored reviews and conservative evidence from fresh analysis."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from price_action_learning.evaluation import Evaluation
from price_action_learning.evaluation.core import _validated_attempt
from price_action_learning.learning_state import LearningState
from price_action_learning.learning_state.core import _check_state_values
from price_action_learning.training import TrainingAttempt
from price_action_learning.training.core import (
    KnowledgeBoundary, LearningMapReference, TrainingContext,
    _allowed_for_stage, _canonical_learning_map_reference,
)


_STAGES = ('S1', 'S2', 'S3')
_SKILLS = ('SKL-S1-MARKET-STATE', 'SKL-S2-STRUCTURE-MOVEMENT',
           'SKL-S3-MARKET-LOCATION')
# Membership only, pinned Learning Map blob
# 726b35db8409ea03cbec33c916db7374e6724e03. Evaluation owns Error eligibility.
_ERRORS = ('OBS-001', 'OBS-002', 'OBS-004', 'STR-001', 'STR-002', 'STR-006',
           'STR-007', 'STR-003', 'STR-004', 'STR-005', 'REA-002', 'REA-003',
           'REA-005', 'LOC-001', 'LOC-002', 'LOC-003', 'LOC-004', 'LOC-005', 'LOC-006')
_RESULTS = ('REPEATED', 'IMPROVING', 'RESOLVED', 'INCONCLUSIVE')
_DAYS = (3, 7, 30)


@dataclass(frozen=True, slots=True, init=False)
class ReviewRecord:
    """Exactly seven persistent fields; creation belongs to Review operations."""

    id: str
    source_attempt_id: str
    error_id: str
    scheduled_for: datetime
    completed_at: datetime | None
    new_analysis: str | None
    result: str | None

    def __new__(cls, *args, **kwargs):
        raise TypeError('ReviewRecord must be created through Review operations')

    def __setstate__(self, state):
        raise TypeError('ReviewRecord state restoration is not supported')

    def __reduce__(self):
        raise TypeError('ReviewRecord pickle serialization is not supported')

    def __reduce_ex__(self, protocol):
        raise TypeError('ReviewRecord pickle serialization is not supported')


def _text(value, field):
    if type(value) is not str or not value.strip():
        raise ValueError(f'{field} must be a nonempty base string')
    return value


def _choice(value, choices, field):
    if type(value) is not str or value not in choices:
        raise ValueError(f'{field} must be canonical')
    return value


def _uuid(value, field):
    if type(value) is not str:
        raise ValueError(f'{field} must be a canonical UUID4 string')
    parsed = UUID(value)
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError(f'{field} must be a canonical UUID4 string')
    return value


def _utc(value, field):
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f'{field} must be an exact UTC datetime')
    return value


def _knowledge(boundary, stage):
    """Read the published historical boundary without constructing a submission."""
    if type(boundary) is not KnowledgeBoundary:
        raise ValueError('knowledge_boundary must be the published exact type')
    _choice(boundary.stage, _STAGES, 'boundary.stage')
    if boundary.stage != stage:
        raise ValueError('historical boundary Stage must match the submission')
    allowed, learned = boundary.allowed_concept_ids, boundary.learned_concept_ids
    if type(allowed) is not frozenset or type(learned) is not frozenset:
        raise ValueError('knowledge sets must retain canonical immutable shape')
    # Check each supplied element before a union or equality can discard a
    # noncanonical string subclass that spoofs equality with an allowed Concept.
    for collection in (allowed, learned):
        for value in collection:
            _text(value, 'Concept ID')
    if allowed != _allowed_for_stage(stage) or not learned <= allowed:
        raise ValueError('knowledge must retain the published Stage boundary')
    confidence = boundary.concept_confidence
    if type(confidence) is not tuple:
        raise ValueError('knowledge confidence must be an exact tuple')
    for pair in confidence:
        if type(pair) is not tuple or len(pair) != 2:
            raise ValueError('knowledge confidence must contain canonical pairs')
        _text(pair[0], 'Concept ID')
        _choice(pair[1], ('CORE',), 'knowledge confidence')
    if confidence != tuple((concept, 'CORE') for concept in sorted(allowed)):
        raise ValueError('knowledge confidence must retain the published CORE boundary')
    reference = boundary.learning_map_reference
    if type(reference) is not LearningMapReference:
        raise ValueError('Learning Map reference must retain the published type')
    for name in ('commit', 'path', 'blob'):
        _text(getattr(reference, name), 'Learning Map reference')
    if reference != _canonical_learning_map_reference():
        raise ValueError('Learning Map reference must identify the pinned specification')
    return learned


def _metadata(attempt):
    """Read source identity, schedule, Stage and knowledge; never its old answer."""
    if type(attempt) is not TrainingAttempt:
        raise ValueError('attempt must be the exact published TrainingAttempt')
    _uuid(attempt.id, 'attempt.id')
    _utc(attempt.created_at, 'attempt.created_at')
    _choice(attempt.stage, _STAGES, 'attempt.stage')
    if type(attempt.context) is not TrainingContext:
        raise ValueError('context must retain the published exact type')
    return _knowledge(attempt.context.knowledge_boundary, attempt.stage)


def _formal_errors(evaluation, attempt):
    """Validate observable Evaluation shape, without rerunning Error judgment."""
    if type(evaluation) is not Evaluation:
        raise ValueError('evaluation must be the exact published Evaluation')
    _uuid(evaluation.attempt_id, 'evaluation.attempt_id')
    if evaluation.attempt_id != attempt.id:
        raise ValueError('evaluation must bind the supplied original submission')
    _choice(evaluation.skill_signal, _SKILLS, 'skill_signal')
    _choice(evaluation.evaluation_confidence, ('HIGH', 'MEDIUM', 'LOW'), 'evaluation_confidence')
    if type(evaluation.abstain) is not bool:
        raise ValueError('abstain must be a strict bool')
    primary = evaluation.primary_error
    if primary is not None:
        _choice(primary, _ERRORS, 'primary_error')
    contributors = evaluation.contributors
    if type(contributors) is not tuple or len(contributors) > 2:
        raise ValueError('contributors must be an exact tuple of at most two Errors')
    for error in contributors:
        _choice(error, _ERRORS, 'contributor')
    if len(set(contributors)) != len(contributors) or primary in contributors:
        raise ValueError('formal Errors must be distinct')
    if evaluation.abstain and (primary is not None or contributors):
        raise ValueError('abstention cannot contain formal Errors')
    if evaluation.evaluation_confidence == 'LOW' and not evaluation.abstain:
        raise ValueError('LOW confidence requires abstention')
    if type(evaluation.what_was_correct) is not tuple:
        raise ValueError('what_was_correct must retain its canonical immutable shape')
    for text in evaluation.what_was_correct:
        _text(text, 'what_was_correct')
    for name in ('primary_issue', 'hint'):
        value = getattr(evaluation, name)
        if value is not None:
            _text(value, name)
    return (() if primary is None else (primary,)) + contributors


def _check_record(record):
    if type(record) is not ReviewRecord:
        raise ValueError('record must be the exact ReviewRecord type')
    _uuid(record.id, 'record.id')
    _uuid(record.source_attempt_id, 'source_attempt_id')
    _choice(record.error_id, _ERRORS, 'error_id')
    _utc(record.scheduled_for, 'scheduled_for')
    completion = (record.completed_at, record.new_analysis, record.result)
    if all(value is None for value in completion):
        return
    if any(value is None for value in completion):
        raise ValueError('completion fields must be all None or all present')
    _utc(record.completed_at, 'completed_at')
    if record.completed_at < record.scheduled_for:
        raise ValueError('completion cannot precede the scheduled review')
    _text(record.new_analysis, 'new_analysis')
    _choice(record.result, _RESULTS, 'result')


def _build_record(*, id, source_attempt_id, error_id, scheduled_for,
                  completed_at=None, new_analysis=None, result=None):
    record = object.__new__(ReviewRecord)
    values = (id, source_attempt_id, error_id, scheduled_for, completed_at, new_analysis, result)
    for name, value in zip(ReviewRecord.__slots__, values):
        object.__setattr__(record, name, value)
    _check_record(record)
    return record


def _slots(source):
    return tuple(source.created_at + timedelta(days=day) for day in _DAYS)


def schedule_reviews(*, state: LearningState, source_attempt: TrainingAttempt,
                     evaluation: Evaluation) -> tuple[ReviewRecord, ...]:
    """Create three targeted scheduled records; retain and mutate no learner state."""
    try:
        if type(state) is not LearningState:
            raise ValueError('state must be the exact published LearningState')
        _check_state_values(state.current_stage, state.skills, state.errors,
                            state.current_focus, state.reviews_due)
        _metadata(source_attempt)
        _validated_attempt(source_attempt)
        formal = _formal_errors(evaluation, source_attempt)
        if state.current_stage != source_attempt.stage:
            raise ValueError('state Stage must match the source submission')
        if evaluation.abstain or not formal:
            raise ValueError('scheduling requires non-abstaining formal Error evidence')
        if state.current_focus is None or state.current_focus not in formal:
            raise ValueError('current_focus must be formally identified in the source Evaluation')
        identities = tuple(str(uuid4()) for _ in _DAYS)
        if len(set(identities)) != 3:
            raise ValueError('scheduled Review IDs must be distinct')
        return tuple(_build_record(id=id, source_attempt_id=source_attempt.id,
                                   error_id=state.current_focus, scheduled_for=slot)
                     for id, slot in zip(identities, _slots(source_attempt)))
    except (AttributeError, TypeError, OverflowError) as exc:
        raise ValueError('scheduling inputs must retain their canonical invariants') from exc


def _resolution(prior_reviews, record, source, completed_at):
    """Only target-absent day-30 uses predecessor evidence. Missing is valid."""
    if type(prior_reviews) is not tuple or len(prior_reviews) > 2:
        raise ValueError('resolution evidence must be an exact tuple of zero to two predecessors')
    slots = _slots(source)[:2]
    ids = {record.id}
    positions = []
    for prior in prior_reviews:
        _check_record(prior)
        if prior.source_attempt_id != record.source_attempt_id or prior.error_id != record.error_id:
            raise ValueError('predecessors must match source and targeted Error')
        if prior.completed_at is None or prior.completed_at > completed_at:
            raise ValueError('predecessors must be completed by current completion')
        if prior.id in ids:
            raise ValueError('predecessor IDs must be distinct')
        ids.add(prior.id)
        if prior.scheduled_for not in slots:
            raise ValueError('predecessors must use exact source-anchored day-3 or day-7 slots')
        positions.append(slots.index(prior.scheduled_for))
    if len(positions) == 2 and positions != [0, 1]:
        raise ValueError('a two-record chain must be exactly day-3 then day-7')
    if len(prior_reviews) == 2 and all(prior.result == 'IMPROVING' for prior in prior_reviews):
        return 'RESOLVED'
    return 'IMPROVING'


def complete_review(*, record: ReviewRecord, source_attempt: TrainingAttempt,
                    review_attempt: TrainingAttempt, review_evaluation: Evaluation,
                    completed_at: datetime, prior_reviews=()) -> ReviewRecord:
    """Consume a fresh original analysis and Evaluation; return new Review evidence."""
    try:
        _check_record(record)
        if record.completed_at is not None:
            raise ValueError('record must be an uncompleted scheduled review')
        source_learned = _metadata(source_attempt)
        review_learned = _metadata(review_attempt)
        _validated_attempt(review_attempt)  # Preserve the supplied original; never reconstruct it.
        _text(review_attempt.user_analysis, 'fresh user_analysis')
        if record.source_attempt_id != source_attempt.id:
            raise ValueError('record must bind the source submission')
        slots = _slots(source_attempt)
        if record.scheduled_for not in slots:
            raise ValueError('record must use a canonical source-anchored review slot')
        _utc(completed_at, 'completed_at')
        if completed_at < record.scheduled_for:
            raise ValueError('completion cannot precede the scheduled review')
        if review_attempt.id == source_attempt.id or review_attempt.stage != source_attempt.stage:
            raise ValueError('review must be a fresh submission at the historical Stage')
        context = review_attempt.context
        _choice(context.training_mode, ('FOCUSED',), 'review training_mode')
        _choice(context.focus_error_id, _ERRORS, 'review focus_error_id')
        if context.focus_error_id != record.error_id:
            raise ValueError('fresh review focus must match the targeted Error')
        if not source_learned <= review_learned:
            raise ValueError('historical learned knowledge cannot regress')
        formal = _formal_errors(review_evaluation, review_attempt)
        if review_evaluation.abstain:
            outcome = 'INCONCLUSIVE'
        elif record.error_id in formal:
            outcome = 'REPEATED'
        elif record.scheduled_for != slots[2]:
            outcome = 'IMPROVING'
        else:
            outcome = _resolution(prior_reviews, record, source_attempt, completed_at)
        return _build_record(id=record.id, source_attempt_id=record.source_attempt_id,
                             error_id=record.error_id, scheduled_for=record.scheduled_for,
                             completed_at=completed_at, new_analysis=review_attempt.user_analysis,
                             result=outcome)
    except (AttributeError, TypeError, OverflowError) as exc:
        raise ValueError('completion inputs must retain their canonical invariants') from exc
