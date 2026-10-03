"""Conservative state transitions from an already-authorized Evaluation."""

from dataclasses import dataclass

from price_action_learning.evaluation import Evaluation
from price_action_learning.evaluation.core import _validated_attempt
from price_action_learning.training import TrainingAttempt


_STAGES = ("S1", "S2", "S3")
_SKILL_IDS = ("SKL-S1-MARKET-STATE", "SKL-S2-STRUCTURE-MOVEMENT",
              "SKL-S3-MARKET-LOCATION")
_SKILL_STATUSES = ("NOT_STARTED", "LEARNING", "UNSTABLE", "STABLE")
# Identifier membership/order only, from the published Learning Map blob
# 726b35db8409ea03cbec33c916db7374e6724e03. Judgment belongs to Evaluation.
_ERROR_IDS = ("OBS-001", "OBS-002", "OBS-004", "STR-001", "STR-002",
              "STR-006", "STR-007", "STR-003", "STR-004", "STR-005",
              "REA-002", "REA-003", "REA-005", "LOC-001", "LOC-002",
              "LOC-003", "LOC-004", "LOC-005", "LOC-006")
_ERROR_STATUSES = ("NEW", "REPEATED", "FOCUS", "IMPROVING", "RESOLVED")


@dataclass(frozen=True, slots=True, init=False)
class LearningState:
    """Exactly five immutable fields; construction belongs to the factories."""

    current_stage: str
    skills: tuple[tuple[str, str], ...]
    errors: tuple[tuple[str, str], ...]
    current_focus: str | None
    reviews_due: tuple[str, ...]

    def __new__(cls, *args, **kwargs):
        raise TypeError("LearningState must be created through its validated operations")

    def __setstate__(self, state):
        raise TypeError("LearningState state restoration is not supported")

    def __reduce__(self):
        raise TypeError("LearningState pickle serialization is not supported")

    def __reduce_ex__(self, protocol):
        raise TypeError("LearningState pickle serialization is not supported")


def _text(value, field):
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field} must be a non-empty base string")
    return value


def _choice(value, choices, field):
    if type(value) is not str or value not in choices:
        raise ValueError(f"{field} must be canonical")
    return value


def _check_state_values(current_stage, skills, errors, current_focus, reviews_due):
    _choice(current_stage, _STAGES, "current_stage")
    if type(skills) is not tuple or len(skills) != len(_SKILL_IDS):
        raise ValueError("skills must contain exactly the three ordered Skill/status pairs")
    for pair, expected_id in zip(skills, _SKILL_IDS):
        if type(pair) is not tuple or len(pair) != 2:
            raise ValueError("skills must contain immutable pairs")
        _choice(pair[0], (expected_id,), "Skill ID/order")
        _choice(pair[1], _SKILL_STATUSES, "Skill status")
    if type(errors) is not tuple:
        raise ValueError("errors must contain immutable ordered Error/status pairs")
    seen = set()
    previous_position = -1
    for pair in errors:
        if type(pair) is not tuple or len(pair) != 2:
            raise ValueError("errors must contain immutable pairs")
        error = _choice(pair[0], _ERROR_IDS, "Error ID")
        _choice(pair[1], _ERROR_STATUSES, "Error status")
        position = _ERROR_IDS.index(error)
        if position <= previous_position:
            raise ValueError("errors must be unique and in canonical published order")
        previous_position = position
        seen.add(error)
    if current_focus is not None:
        _choice(current_focus, _ERROR_IDS, "current_focus")
        if current_focus not in seen:
            raise ValueError("current_focus must be represented in errors")
    if type(reviews_due) is not tuple:
        raise ValueError("reviews_due must be an immutable tuple")
    for value in reviews_due:
        _text(value, "reviews_due member")


def _build_state(*, current_stage, skills, errors, current_focus, reviews_due):
    """Private validated allocation, also usable for canonical prior-state tests."""
    _check_state_values(current_stage, skills, errors, current_focus, reviews_due)
    values = (current_stage, skills, errors, current_focus, reviews_due)
    result = object.__new__(LearningState)
    for field, value in zip(LearningState.__slots__, values):
        object.__setattr__(result, field, value)
    return result


def create_learning_state(*, current_stage: str) -> LearningState:
    """Create an initial state at one explicit Stage without scheduling Review."""
    return _build_state(current_stage=current_stage,
                        skills=tuple((skill, "NOT_STARTED") for skill in _SKILL_IDS),
                        errors=(), current_focus=None, reviews_due=())


def _check_inputs(state, attempt, evaluation):
    if type(state) is not LearningState:
        raise ValueError("state must be a canonical LearningState")
    if type(attempt) is not TrainingAttempt:
        raise ValueError("attempt must be the published TrainingAttempt type")
    if type(evaluation) is not Evaluation:
        raise ValueError("evaluation must be the published Evaluation type")
    try:
        _check_state_values(state.current_stage, state.skills, state.errors,
                            state.current_focus, state.reviews_due)
        _choice(attempt.stage, _STAGES, "attempt Stage")
        # Reuse the pinned dependency's observable submission-shape validator.
        # It returns the supplied original attempt; no replacement submission,
        # evaluation, Error eligibility calculation or analysis judgment occurs.
        _validated_attempt(attempt)
        _text(evaluation.attempt_id, "evaluation.attempt_id")
        if evaluation.attempt_id != attempt.id:
            raise ValueError("Evaluation must bind the supplied original attempt")
        if state.current_stage != attempt.stage:
            raise ValueError("Learning State and attempt Stage must match")
        _choice(evaluation.skill_signal, _SKILL_IDS, "skill_signal")
        _choice(evaluation.evaluation_confidence, ("HIGH", "MEDIUM", "LOW"),
                "evaluation_confidence")
        if type(evaluation.abstain) is not bool:
            raise ValueError("abstain must be a strict bool")
        if evaluation.primary_error is not None:
            _choice(evaluation.primary_error, _ERROR_IDS, "primary_error")
        contributors = evaluation.contributors
        if type(contributors) is not tuple or len(contributors) > 2:
            raise ValueError("contributors must be a canonical tuple with at most two Errors")
        for error in contributors:
            _choice(error, _ERROR_IDS, "contributor")
        if len(set(contributors)) != len(contributors):
            raise ValueError("contributors must be unique")
        if evaluation.primary_error is not None and evaluation.primary_error in contributors:
            raise ValueError("primary_error cannot also be a contributor")
        if evaluation.abstain and (evaluation.primary_error is not None or contributors):
            raise ValueError("abstention cannot contain formal Errors")
        if evaluation.evaluation_confidence == "LOW" and not evaluation.abstain:
            raise ValueError("LOW confidence requires abstention")
        if type(evaluation.what_was_correct) is not tuple:
            raise ValueError("what_was_correct must retain its canonical immutable shape")
        for value in evaluation.what_was_correct:
            _text(value, "what_was_correct member")
        for field in ("primary_issue", "hint"):
            value = getattr(evaluation, field)
            if value is not None:
                _text(value, field)
    except (AttributeError, TypeError) as exc:
        raise ValueError("inputs must retain their canonical observable invariants") from exc


def apply_evaluation(*, state: LearningState, attempt: TrainingAttempt,
                     evaluation: Evaluation) -> LearningState:
    """Record canonical structured feedback without mutating any input."""
    _check_inputs(state, attempt, evaluation)
    skills, errors, focus = state.skills, state.errors, state.current_focus
    if not evaluation.abstain:
        formal = (() if evaluation.primary_error is None else (evaluation.primary_error,)) + evaluation.contributors
        skills = tuple((skill, "UNSTABLE" if formal else
                        "LEARNING" if status == "NOT_STARTED" else status)
                       if skill == evaluation.skill_signal else (skill, status)
                       for skill, status in state.skills)
        if formal:
            prior = dict(state.errors)
            focus = next((error for error in formal if error in prior), formal[0])
            updated = dict(prior)
            for error in formal:
                updated[error] = ("NEW" if error not in prior else
                                  "FOCUS" if error == focus else "REPEATED")
            errors = tuple((error, updated[error]) for error in _ERROR_IDS if error in updated)
    return _build_state(current_stage=state.current_stage, skills=skills, errors=errors,
                        current_focus=focus, reviews_due=state.reviews_due)
