"""Learning State contract, transitions and supported reconstruction attacks."""

import copy
import importlib
import importlib.util
import inspect
import pickle
import re
import unittest
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from price_action_learning.evaluation import Evaluation, create_evaluation
from price_action_learning.training import TrainingAttempt, create_training_attempt


SKILLS = ("SKL-S1-MARKET-STATE", "SKL-S2-STRUCTURE-MOVEMENT",
          "SKL-S3-MARKET-LOCATION")
INITIAL_SKILLS = tuple((skill, "NOT_STARTED") for skill in SKILLS)
ERROR_IDS = ("OBS-001", "OBS-002", "OBS-004", "STR-001", "STR-002",
             "STR-006", "STR-007", "STR-003", "STR-004", "STR-005",
             "REA-002", "REA-003", "REA-005", "LOC-001", "LOC-002",
             "LOC-003", "LOC-004", "LOC-005", "LOC-006")
STATE_FIELDS = ("current_stage", "skills", "errors", "current_focus", "reviews_due")


class SpoofText(str):
    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash("S1")


class EqualSpoof:
    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash("S1")


def error_rows():
    text = (Path(__file__).resolve().parents[2]
            / "spec/learning_map/LEARNING_MAP_SPEC.md").read_text(encoding="utf-8")
    rows = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 4 and re.fullmatch(r"`(?:OBS|STR|REA|LOC)-\d{3}`", cells[0]):
            rows.append((cells[0].strip("`"), cells[1], cells[2].strip("`"),
                         tuple(re.findall(r"`(CON-[A-Z0-9-]+)`", cells[3]))))
    return tuple(rows)


class LearningStateTests(unittest.TestCase):
    def setUp(self):
        # Missing API is an assertion failure in the initial RED run.
        self.assertIsNotNone(importlib.util.find_spec("price_action_learning.learning_state"),
                             "the approved Learning State API must exist")
        self.api = importlib.import_module("price_action_learning.learning_state")
        self.core = importlib.import_module("price_action_learning.learning_state.core")

    def initial(self, stage="S1"):
        return self.api.create_learning_state(current_stage=stage)

    def attempt(self, stage="S1", learned=None):
        values = dict(stage=stage, market_scenario="A synthetic observed interval",
                      observation_task="Describe the visible interval",
                      primary_objective="Separate observation from interpretation",
                      target_concept_id="CON-S1-HIGH", training_mode="FORMAL",
                      learned_concept_ids=(), user_analysis="The interval has a visible high.")
        if learned is None:
            seed = create_training_attempt(**values)
            learned = seed.context.knowledge_boundary.allowed_concept_ids
        values["learned_concept_ids"] = learned
        return create_training_attempt(**values)

    def evaluation(self, attempt, **overrides):
        values = dict(attempt=attempt, evaluation_confidence="HIGH", abstain=False)
        values.update(overrides)
        return create_evaluation(**values)

    def apply(self, state, attempt=None, **signals):
        attempt = self.attempt(state.current_stage) if attempt is None else attempt
        return self.api.apply_evaluation(state=state, attempt=attempt,
                                         evaluation=self.evaluation(attempt, **signals))

    def prior(self, **overrides):
        values = dict(current_stage="S1", skills=INITIAL_SKILLS, errors=(),
                      current_focus=None, reviews_due=())
        values.update(overrides)
        return self.core._build_state(**values)

    def snapshot(self, record):
        return tuple(getattr(record, field.name) for field in fields(record))

    def forged(self, record, **overrides):
        # Malformed fixtures, not a supported creation/provenance mechanism.
        result = object.__new__(type(record))
        for field in fields(record):
            object.__setattr__(result, field.name,
                               overrides.get(field.name, getattr(record, field.name)))
        return result

    def assert_bad_apply(self, **overrides):
        state = self.initial()
        attempt = self.attempt()
        evaluation = self.evaluation(attempt)
        args = dict(state=state, attempt=attempt, evaluation=evaluation)
        args.update(overrides)
        before = [self.snapshot(record) for record in (state, attempt, evaluation)]
        with self.assertRaises(ValueError):
            self.api.apply_evaluation(**args)
        self.assertEqual(before, [self.snapshot(record) for record in (state, attempt, evaluation)])

    def test_01_initial_states_for_every_stage(self):
        for stage in ("S1", "S2", "S3"):
            with self.subTest(stage=stage):
                state = self.initial(stage)
                self.assertEqual(self.snapshot(state), (stage, INITIAL_SKILLS, (), None, ()))
                self.assertIs(type(state), self.api.LearningState)

    def test_02_exact_five_fields_slots_and_exports(self):
        state = self.initial()
        self.assertEqual(tuple(field.name for field in fields(state)), STATE_FIELDS)
        self.assertEqual(state.__slots__, STATE_FIELDS)
        self.assertFalse(hasattr(state, "__dict__"))
        self.assertEqual(self.api.__all__, ["LearningState", "create_learning_state", "apply_evaluation"])
        self.assertFalse(hasattr(self.api, "_build_state"))

    def test_03_initial_stage_must_be_explicit_exact_base_string(self):
        with self.assertRaises(TypeError):
            self.api.create_learning_state()
        with self.assertRaises(TypeError):
            self.api.create_learning_state("S1")
        for stage in (None, 1, "S4", "S8", "s1", " S1", "", EqualSpoof(), SpoofText("S1")):
            with self.subTest(stage=type(stage)), self.assertRaises(ValueError):
                self.api.create_learning_state(current_stage=stage)

    def test_04_correct_evaluation_starts_learning_for_each_stage(self):
        for index, stage in enumerate(("S1", "S2", "S3")):
            state = self.initial(stage)
            result = self.apply(state)
            expected = list(INITIAL_SKILLS)
            expected[index] = (SKILLS[index], "LEARNING")
            self.assertEqual(result.skills, tuple(expected))
            self.assertEqual((result.current_stage, result.errors, result.current_focus, result.reviews_due),
                             (stage, (), None, ()))

    def test_05_correct_evaluation_preserves_each_canonical_skill_status(self):
        for status, expected in (("NOT_STARTED", "LEARNING"), ("LEARNING", "LEARNING"),
                                 ("UNSTABLE", "UNSTABLE"), ("STABLE", "STABLE")):
            with self.subTest(status=status):
                state = self.prior(skills=((SKILLS[0], status),) + INITIAL_SKILLS[1:])
                self.assertEqual(self.apply(state).skills, ((SKILLS[0], expected),) + INITIAL_SKILLS[1:])

    def test_06_primary_error_marks_only_signaled_skill_unstable(self):
        state = self.initial("S3")
        result = self.apply(state, primary_error="OBS-001")
        self.assertEqual(result.skills, ((SKILLS[0], "UNSTABLE"),) + INITIAL_SKILLS[1:])
        self.assertEqual(result.current_stage, "S3")

    def test_07_contributor_only_marks_skill_and_selects_first(self):
        result = self.apply(self.initial(), contributors=("OBS-002", "OBS-001"))
        self.assertEqual(result.skills[0], (SKILLS[0], "UNSTABLE"))
        self.assertEqual(result.current_focus, "OBS-002")
        self.assertEqual(result.errors, (("OBS-001", "NEW"), ("OBS-002", "NEW")))

    def test_08_first_primary_focus_remains_new(self):
        result = self.apply(self.initial(), primary_error="OBS-001")
        self.assertEqual((result.errors, result.current_focus), ((("OBS-001", "NEW"),), "OBS-001"))

    def test_09_second_occurrence_becomes_focus(self):
        first = self.apply(self.initial(), primary_error="OBS-001")
        second = self.apply(first, primary_error="OBS-001")
        self.assertEqual((second.errors, second.current_focus), ((("OBS-001", "FOCUS"),), "OBS-001"))
        self.assertEqual(first.errors, (("OBS-001", "NEW"),))

    def test_10_repeated_contributor_outranks_new_primary(self):
        state = self.prior(errors=(("OBS-002", "NEW"),), current_focus="OBS-002")
        result = self.apply(state, primary_error="OBS-001", contributors=("OBS-002",))
        self.assertEqual(result.current_focus, "OBS-002")
        self.assertEqual(result.errors, (("OBS-001", "NEW"), ("OBS-002", "FOCUS")))

    def test_11_first_repeated_in_formal_order_wins(self):
        state = self.prior(errors=(("OBS-001", "NEW"), ("OBS-002", "RESOLVED"), ("OBS-004", "IMPROVING")))
        result = self.apply(state, primary_error="OBS-004", contributors=("OBS-002", "OBS-001"))
        self.assertEqual(result.current_focus, "OBS-004")
        self.assertEqual(result.errors, (("OBS-001", "REPEATED"), ("OBS-002", "REPEATED"), ("OBS-004", "FOCUS")))

    def test_12_contributor_order_controls_repeated_priority(self):
        state = self.prior(errors=(("OBS-001", "NEW"), ("OBS-002", "NEW")))
        for contributors, focus in ((("OBS-002", "OBS-001"), "OBS-002"),
                                    (("OBS-001", "OBS-002"), "OBS-001")):
            with self.subTest(contributors=contributors):
                result = self.apply(state, primary_error="OBS-004", contributors=contributors)
                self.assertEqual(result.current_focus, focus)
                self.assertEqual(dict(result.errors)[focus], "FOCUS")
                self.assertEqual(dict(result.errors)["OBS-004"], "NEW")

    def test_13_all_new_errors_choose_primary_before_contributors(self):
        result = self.apply(self.initial(), primary_error="OBS-004", contributors=("OBS-002", "OBS-001"))
        self.assertEqual(result.current_focus, "OBS-004")
        self.assertEqual(result.errors, (("OBS-001", "NEW"), ("OBS-002", "NEW"), ("OBS-004", "NEW")))

    def test_14_selected_recurrence_from_every_error_status(self):
        for status in ("NEW", "REPEATED", "FOCUS", "IMPROVING", "RESOLVED"):
            with self.subTest(status=status):
                state = self.prior(errors=(("OBS-001", status),), current_focus="OBS-001")
                result = self.apply(state, primary_error="OBS-001")
                self.assertEqual(result.errors, (("OBS-001", "FOCUS"),))
                self.assertEqual(state.errors, (("OBS-001", status),))

    def test_15_nonselected_recurrence_from_every_error_status(self):
        for status in ("NEW", "REPEATED", "FOCUS", "IMPROVING", "RESOLVED"):
            with self.subTest(status=status):
                state = self.prior(errors=(("OBS-001", "NEW"), ("OBS-002", status)))
                result = self.apply(state, primary_error="OBS-001", contributors=("OBS-002",))
                self.assertEqual(result.errors, (("OBS-001", "FOCUS"), ("OBS-002", "REPEATED")))

    def test_16_unrelated_errors_preserve_all_prior_statuses(self):
        for status in ("NEW", "REPEATED", "FOCUS", "IMPROVING", "RESOLVED"):
            state = self.prior(errors=(("OBS-002", status),), current_focus="OBS-002")
            result = self.apply(state, primary_error="OBS-001")
            self.assertEqual(result.errors, (("OBS-001", "NEW"), ("OBS-002", status)))

    def test_17_no_error_preserves_errors_focus_and_reviews(self):
        state = self.prior(errors=(("OBS-001", "FOCUS"), ("OBS-002", "IMPROVING")),
                           current_focus="OBS-001", reviews_due=("future-review-reference",))
        result = self.apply(state)
        self.assertEqual((result.errors, result.current_focus, result.reviews_due),
                         (state.errors, state.current_focus, state.reviews_due))
        self.assertEqual(result.skills[0], (SKILLS[0], "LEARNING"))

    def test_18_abstention_is_new_semantically_identical_state(self):
        state = self.prior(skills=((SKILLS[0], "STABLE"),) + INITIAL_SKILLS[1:],
                           errors=(("OBS-001", "RESOLVED"),), current_focus="OBS-001",
                           reviews_due=("already-due",))
        for confidence in ("HIGH", "MEDIUM", "LOW"):
            result = self.apply(state, abstain=True, evaluation_confidence=confidence)
            self.assertIsNot(result, state)
            self.assertEqual(self.snapshot(result), self.snapshot(state))

    def test_19_existing_reviews_are_preserved_without_scheduling(self):
        for signals in ({}, {"primary_error": "OBS-001"}, {"abstain": True}):
            state = self.prior(reviews_due=("opaque-reference-one", "opaque-reference-two"))
            result = self.apply(state, **signals)
            self.assertEqual(result.reviews_due, ("opaque-reference-one", "opaque-reference-two"))

    def test_20_stage_never_advances(self):
        for stage in ("S1", "S2", "S3"):
            for signals in ({}, {"primary_error": "OBS-001"}, {"abstain": True}):
                self.assertEqual(self.apply(self.initial(stage), **signals).current_stage, stage)

    def test_21_every_published_error_is_recorded_with_its_evaluation_skill(self):
        rows = error_rows()
        self.assertEqual(tuple(row[0] for row in rows), ERROR_IDS)
        for error, stage, skill, concepts in rows:
            with self.subTest(error=error):
                attempt = self.attempt(stage, concepts)
                state = self.initial(stage)
                result = self.apply(state, attempt, primary_error=error)
                self.assertEqual(result.errors, ((error, "NEW"),))
                self.assertEqual(result.current_focus, error)
                self.assertEqual(dict(result.skills)[skill], "UNSTABLE")

    def test_22_storage_uses_published_order_instead_of_lexical_order(self):
        state = self.initial("S3")
        for error in reversed(ERROR_IDS):
            state = self.apply(state, primary_error=error)
        self.assertEqual(state.errors, tuple((error, "NEW") for error in ERROR_IDS))

    def test_23_skill_signal_consumed_without_error_judgment_rerun(self):
        attempt = self.attempt("S3")
        evaluation = self.evaluation(attempt, primary_error="OBS-001", contributors=("LOC-001",))
        with patch("price_action_learning.evaluation.core._error_skill", side_effect=AssertionError("judgment rerun")), \
             patch("price_action_learning.evaluation.core.create_evaluation", side_effect=AssertionError("replacement Evaluation")), \
             patch("price_action_learning.training.core.create_training_attempt", side_effect=AssertionError("replacement attempt")):
            result = self.api.apply_evaluation(state=self.initial("S3"), attempt=attempt, evaluation=evaluation)
        self.assertEqual(result.skills, ((SKILLS[0], "UNSTABLE"),) + INITIAL_SKILLS[1:])
        self.assertEqual(result.errors, (("OBS-001", "NEW"), ("LOC-001", "NEW")))

    def test_24_attempt_identity_mismatch_rejects(self):
        first, second = self.attempt(), self.attempt()
        self.assert_bad_apply(attempt=first, evaluation=self.evaluation(second))

    def test_25_state_attempt_stage_mismatch_rejects_even_abstention(self):
        attempt = self.attempt("S2")
        for abstain in (False, True):
            self.assert_bad_apply(attempt=attempt, evaluation=self.evaluation(attempt, abstain=abstain))

    def test_26_duck_none_and_incomplete_records_reject(self):
        attempt = self.attempt()
        state, evaluation = self.initial(), self.evaluation(attempt)
        for key, record in (("state", state), ("attempt", attempt), ("evaluation", evaluation)):
            duck = SimpleNamespace(**{field.name: getattr(record, field.name) for field in fields(record)})
            for value in (duck, None, object(), object.__new__(type(record))):
                with self.subTest(key=key, kind=type(value)):
                    self.assert_bad_apply(**{key: value})

    def test_27_record_subclasses_reject(self):
        for key, cls in (("state", self.api.LearningState), ("attempt", TrainingAttempt), ("evaluation", Evaluation)):
            subclass = type("UnsupportedSubclass", (cls,), {})
            with self.assertRaises(TypeError):
                subclass()
            self.assert_bad_apply(**{key: object.__new__(subclass)})

    def test_28_attempt_consumed_identifier_stage_and_status_spoofs_reject(self):
        for field, value in (("id", EqualSpoof()), ("id", SpoofText("arbitrary")),
                             ("stage", SpoofText("S1")), ("stage", EqualSpoof()),
                             ("status", SpoofText("SUBMITTED")), ("revision", "later")):
            attempt = self.attempt()
            evaluation = self.evaluation(attempt)
            self.assert_bad_apply(attempt=self.forged(attempt, **{field: value}), evaluation=evaluation)

    def test_29_evaluation_consumed_values_and_containers_reject_spoofs(self):
        attempt = self.attempt()
        evaluation = self.evaluation(attempt)
        cases = (("attempt_id", EqualSpoof()), ("attempt_id", SpoofText(attempt.id)),
                 ("primary_error", EqualSpoof()), ("primary_error", "UNKNOWN-001"),
                 ("primary_error", SpoofText("OBS-001")), ("contributors", ["OBS-001"]),
                 ("contributors", (SpoofText("OBS-001"),)), ("skill_signal", EqualSpoof()),
                 ("skill_signal", SpoofText(SKILLS[0])), ("skill_signal", "NEW-SKILL"),
                 ("evaluation_confidence", SpoofText("HIGH")), ("abstain", 1))
        for field, value in cases:
            with self.subTest(field=field, kind=type(value)):
                self.assert_bad_apply(attempt=attempt, evaluation=self.forged(evaluation, **{field: value}))

    def test_30_noncanonical_evaluation_cardinality_abstain_and_confidence_reject(self):
        attempt = self.attempt()
        evaluation = self.evaluation(attempt)
        for changes in ({"contributors": ("OBS-001", "OBS-001")},
                        {"contributors": ("OBS-001", "OBS-002", "OBS-004")},
                        {"primary_error": "OBS-001", "contributors": ("OBS-001",)},
                        {"abstain": True, "primary_error": "OBS-001"},
                        {"evaluation_confidence": "LOW"}, {"evaluation_confidence": "UNKNOWN"}):
            with self.subTest(changes=changes):
                self.assert_bad_apply(attempt=attempt, evaluation=self.forged(evaluation, **changes))

    def test_31_malformed_state_shapes_statuses_order_and_focus_reject(self):
        state = self.initial()
        cases = (("current_stage", "S4"), ("current_stage", SpoofText("S1")),
                 ("skills", list(INITIAL_SKILLS)), ("skills", INITIAL_SKILLS[::-1]),
                 ("skills", INITIAL_SKILLS[:-1]),
                 ("skills", ((SKILLS[0], "MASTERED"),) + INITIAL_SKILLS[1:]),
                 ("skills", ((SKILLS[0], SpoofText("STABLE")),) + INITIAL_SKILLS[1:]),
                 ("errors", (("UNKNOWN-001", "NEW"),)),
                 ("errors", (("OBS-001", "NEW"), ("OBS-001", "NEW"))),
                 ("errors", (("OBS-002", "NEW"), ("OBS-001", "NEW"))),
                 ("errors", (("OBS-001", "CLEARED"),)),
                 ("errors", ((SpoofText("OBS-001"), "NEW"),)),
                 ("errors", (["OBS-001", "NEW"],)),
                 ("current_focus", "OBS-001"), ("current_focus", EqualSpoof()),
                 ("reviews_due", ["mutable"]), ("reviews_due", ("",)),
                 ("reviews_due", ("  ",)), ("reviews_due", (SpoofText("opaque"),)))
        for field, value in cases:
            with self.subTest(field=field, kind=type(value)):
                self.assert_bad_apply(state=self.forged(state, **{field: value}))

    def test_32_private_builder_validates_before_allocation(self):
        for changes in ({"current_focus": "OBS-001"}, {"errors": (("OBS-001", "UNKNOWN"),)},
                        {"skills": [list(pair) for pair in INITIAL_SKILLS]},
                        {"reviews_due": ["mutable"]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.prior(**changes)

    def test_33_output_fields_and_nested_representations_are_immutable(self):
        state = self.apply(self.initial(), primary_error="OBS-001")
        for field in STATE_FIELDS:
            with self.subTest(field=field), self.assertRaises((FrozenInstanceError, TypeError, AttributeError)):
                setattr(state, field, None)
        with self.assertRaises(TypeError):
            state.skills[0][1] = "STABLE"
        with self.assertRaises(TypeError):
            state.errors[0][1] = "RESOLVED"
        with self.assertRaises((FrozenInstanceError, TypeError, AttributeError)):
            del state.current_stage

    def test_34_success_and_rejection_preserve_all_original_inputs(self):
        state, attempt = self.initial(), self.attempt()
        evaluation = self.evaluation(attempt, primary_error="OBS-001")
        inputs = (state, attempt, evaluation)
        before = tuple(self.snapshot(record) for record in inputs)
        output = self.api.apply_evaluation(state=state, attempt=attempt, evaluation=evaluation)
        self.assertIsNot(output, state)
        self.assertEqual(before, tuple(self.snapshot(record) for record in inputs))
        with self.assertRaises(ValueError):
            self.api.apply_evaluation(state=state, attempt=self.attempt(), evaluation=evaluation)
        self.assertEqual(before, tuple(self.snapshot(record) for record in inputs))

    def test_35_mutable_source_lists_cannot_alias_state(self):
        learned = ["CON-S1-HIGH", "CON-S1-FACT-VS-INTERPRETATION"]
        attempt = self.attempt(learned=learned)
        contributors = ["OBS-002"]
        positives = ["The interval is specified."]
        evaluation = self.evaluation(attempt, primary_error="OBS-001", contributors=contributors,
                                     what_was_correct=positives)
        result = self.api.apply_evaluation(state=self.initial(), attempt=attempt, evaluation=evaluation)
        learned.clear()
        contributors[:] = ["LOC-001"]
        positives.clear()
        self.assertEqual(result.errors, (("OBS-001", "NEW"), ("OBS-002", "NEW")))
        self.assertEqual(evaluation.contributors, ("OBS-002",))
        self.assertEqual(attempt.user_analysis, "The interval has a visible high.")

    def test_36_direct_construction_and_replace_are_blocked(self):
        state = self.initial()
        values = dict(zip(STATE_FIELDS, self.snapshot(state)))
        for args, kwargs in (((), {}), (self.snapshot(state), {}), ((), values), ((), {"token": object()})):
            with self.subTest(args=len(args), kwargs=list(kwargs)), self.assertRaises(TypeError):
                self.api.LearningState(*args, **kwargs)
        with self.assertRaises(TypeError):
            replace(state, current_stage="S3")

    def test_37_copy_deepcopy_pickle_all_protocols_are_blocked(self):
        state = self.initial()
        before = self.snapshot(state)
        for operation in (copy.copy, copy.deepcopy):
            with self.subTest(operation=operation), self.assertRaises(TypeError):
                operation(state)
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.subTest(protocol=protocol), self.assertRaises(TypeError):
                pickle.dumps(state, protocol=protocol)
        self.assertEqual(self.snapshot(state), before)

    def test_38_reduction_and_restoration_reject_without_touching_original(self):
        state = self.initial()
        before = self.snapshot(state)
        for operation in (lambda: state.__reduce__(),
                          lambda: state.__setstate__(["S3", [], [], None, []])):
            with self.assertRaises(TypeError):
                operation()
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.assertRaises(TypeError):
                state.__reduce_ex__(protocol)
        self.assertEqual(self.snapshot(state), before)

    def test_39_standard_pickle_build_restoration_cannot_bypass_factory(self):
        payload = (b"ccopy_reg\n_reconstructor\n(cprice_action_learning.learning_state.core\n"
                   b"LearningState\nc__builtin__\nobject\nNtR(lp0\nVS3\na(la(laNa(lab.")
        with self.assertRaises(TypeError):
            pickle.loads(payload)

    def test_40_public_operations_have_only_approved_keyword_arguments(self):
        for operation, names in ((self.api.create_learning_state, ("current_stage",)),
                                 (self.api.apply_evaluation, ("state", "attempt", "evaluation"))):
            signature = inspect.signature(operation)
            self.assertEqual(tuple(signature.parameters), names)
            self.assertTrue(all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in signature.parameters.values()))
        state, attempt = self.initial(), self.attempt()
        evaluation = self.evaluation(attempt)
        for forbidden in ("current_focus", "future_candles", "future_movement", "realized_pnl",
                          "trade_result", "prediction_result", "market_outcome"):
            with self.subTest(forbidden=forbidden), self.assertRaises(TypeError):
                self.api.apply_evaluation(state=state, attempt=attempt, evaluation=evaluation,
                                          **{forbidden: "forbidden"})

    def test_41_learning_state_does_not_expand_historical_training_authority(self):
        original = self.attempt(learned=["CON-S1-HIGH"])
        before = self.snapshot(original)
        self.apply(self.initial(), original, primary_error="OBS-001")
        for error in ("OBS-002", "LOC-001"):
            for channel in ({"primary_error": error}, {"contributors": (error,)}):
                with self.subTest(error=error, channel=channel), self.assertRaises(ValueError):
                    self.evaluation(original, **channel)
        self.assertEqual(self.snapshot(original), before)

    def test_42_no_error_prose_does_not_supply_formal_errors(self):
        attempt = self.attempt()
        evaluation = self.evaluation(attempt, what_was_correct=("OBS-001 is a label, not a formal signal here.",),
                                     primary_issue="No formal diagnosis.", hint="Use observed evidence.")
        result = self.api.apply_evaluation(state=self.initial(), attempt=attempt, evaluation=evaluation)
        self.assertEqual((result.errors, result.current_focus), ((), None))
        self.assertEqual(result.skills[0], (SKILLS[0], "LEARNING"))

    def test_43_tampered_dependency_nested_mutability_is_rejected(self):
        attempt = self.attempt()
        evaluation = self.evaluation(attempt)
        for context in (None, SimpleNamespace(), []):
            self.assert_bad_apply(attempt=self.forged(attempt, context=context), evaluation=evaluation)
        boundary = attempt.context.knowledge_boundary
        old = boundary.learned_concept_ids
        try:
            object.__setattr__(boundary, "learned_concept_ids", list(old))
            self.assert_bad_apply(attempt=attempt, evaluation=evaluation)
        finally:
            object.__setattr__(boundary, "learned_concept_ids", old)


if __name__ == "__main__":
    unittest.main()
