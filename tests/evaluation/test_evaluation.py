"""PRE first-cycle cases 01-33 and refinements.

Cases 34 (all Training regressions) and 35 (all project test files) are
separate execution checks, avoiding recursive suites inside this suite.
"""

import inspect
import pickle
import re
import unittest
from base64 import b64decode
from dataclasses import FrozenInstanceError, asdict, fields, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from price_action_learning import evaluation
from price_action_learning.evaluation import Evaluation, create_evaluation
from price_action_learning.training import (
    KnowledgeBoundary,
    LearningMapReference,
    TrainingAttempt,
    TrainingContext,
    create_training_attempt,
)


HIGH = "CON-S1-HIGH"
FACT = "CON-S1-FACT-VS-INTERPRETATION"
IMPULSE = "CON-S2-IMPULSE"
LOCATION = "CON-S3-RANGE-HIGH"
SKILLS = {
    "S1": "SKL-S1-MARKET-STATE",
    "S2": "SKL-S2-STRUCTURE-MOVEMENT",
    "S3": "SKL-S3-MARKET-LOCATION",
}
NINE_FIELDS = (
    "attempt_id", "what_was_correct", "primary_issue", "primary_error",
    "contributors", "hint", "skill_signal", "evaluation_confidence", "abstain",
)

# Captured from the PRE-reviewed factory-created S1 record, before the FIX.
# These retain the historical ordinary pickle reconstruction/BUILD route.
HISTORICAL_PICKLE_PAYLOADS = (
    (0, b64decode(
        "Y2NvcHlfcmVnCl9yZWNvbnN0cnVjdG9yCnAwCihjcHJpY2VfYWN0aW9uX2xlYXJu"
        "aW5nLmV2YWx1YXRpb24uY29yZQpFdmFsdWF0aW9uCnAxCmNfX2J1aWx0aW5fXwpv"
        "YmplY3QKcDIKTnRwMwpScDQKKGxwNQpWNDM1NzczMDgtOTI4Ni00YWUxLWJiYjUt"
        "MjE4MWFhZDcxMDdmCnA2CmEodGFOYVZPQlMtMDAxCnA3CmEodGFOYVZTS0wtUzEt"
        "TUFSS0VULVNUQVRFCnA4CmFWSElHSApwOQphSTAwCmFiLg=="
    )),
    (1, b64decode(
        "Y2NvcHlfcmVnCl9yZWNvbnN0cnVjdG9yCnEAKGNwcmljZV9hY3Rpb25fbGVhcm5p"
        "bmcuZXZhbHVhdGlvbi5jb3JlCkV2YWx1YXRpb24KcQFjX19idWlsdGluX18Kb2Jq"
        "ZWN0CnECTnRxA1JxBF1xBShYJAAAADQzNTc3MzA4LTkyODYtNGFlMS1iYmI1LTIx"
        "ODFhYWQ3MTA3ZnEGKU5YBwAAAE9CUy0wMDFxBylOWBMAAABTS0wtUzEtTUFSS0VU"
        "LVNUQVRFcQhYBAAAAEhJR0hxCUkwMAplYi4="
    )),
)


def published_error_rows():
    """Independent expectations from the unchanged, frozen Learning Map spec."""
    path = Path(__file__).resolve().parents[2] / "spec/learning_map/LEARNING_MAP_SPEC.md"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 4 and re.fullmatch(r"`(?:OBS|STR|REA|LOC)-\d{3}`", cells[0]):
            rows.append((cells[0].strip("`"), cells[1], cells[2].strip("`"),
                         tuple(re.findall(r"`(CON-[A-Z0-9-]+)`", cells[3]))))
    return tuple(rows)


ERROR_ROWS = published_error_rows()


class CallerText(str):
    pass


class EqualSpoof:
    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash("OBS-001")

    def __bool__(self):
        return True

    def __str__(self):
        return "OBS-001"


class SpoofText(str):
    def __new__(cls, raw, pretend):
        result = super().__new__(cls, raw)
        result.pretend = pretend
        return result

    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash(self.pretend)

    def __str__(self):
        return self.pretend

    def strip(self, *args):
        return self.pretend


class EvaluationTests(unittest.TestCase):
    def make_attempt(self, stage="S1", learned=None, **overrides):
        values = {
            "stage": stage,
            "market_scenario": "An observed interval with visible highs and lows",
            "observation_task": "Describe the target in the submitted interval",
            "primary_objective": "Describe observable evidence before interpretation",
            "target_concept_id": {"S1": HIGH, "S2": IMPULSE, "S3": LOCATION}[stage],
            "training_mode": "FORMAL",
            "learned_concept_ids": [HIGH] if learned is None else learned,
            "user_analysis": "  The high is observable in the chosen interval.\n",
            "user_confidence": "MEDIUM",
        }
        values.update(overrides)
        return create_training_attempt(**values)

    def evaluate(self, attempt=None, **overrides):
        values = {
            "attempt": self.make_attempt() if attempt is None else attempt,
            "what_was_correct": (),
            "evaluation_confidence": "HIGH",
            "abstain": False,
        }
        values.update(overrides)
        return create_evaluation(**values)

    def tamper(self, attempt, path, value):
        names = path.split(".")
        target = attempt
        for name in names[:-1]:
            target = getattr(target, name)
        object.__setattr__(target, names[-1], value)
        return attempt

    def assert_rejected_error(self, attempt, error):
        for field, value in (("primary_error", error), ("contributors", [error])):
            with self.subTest(field=field, error=str.__str__(error) if isinstance(error, str) else type(error)), self.assertRaises(ValueError):
                self.evaluate(attempt, **{field: value})

    def test_01_canonical_published_attempt_is_accepted(self):
        attempt = self.make_attempt()
        result = self.evaluate(attempt, what_was_correct=["You stated the interval."])
        self.assertIs(type(attempt), TrainingAttempt)
        self.assertIs(type(attempt.context), TrainingContext)
        self.assertIs(type(attempt.context.knowledge_boundary), KnowledgeBoundary)
        self.assertIs(type(attempt.context.knowledge_boundary.learning_map_reference), LearningMapReference)
        self.assertIs(type(result), Evaluation)
        self.assertEqual(result.attempt_id, attempt.id)

    def test_02_duck_typed_or_subclass_attempt_is_rejected(self):
        source = self.make_attempt()
        duck = SimpleNamespace(**{field.name: getattr(source, field.name) for field in fields(source)})
        class AttemptSubclass(TrainingAttempt):
            pass
        with self.assertRaises(TypeError):
            AttemptSubclass()
        subclass = object.__new__(AttemptSubclass)
        for attempt in (duck, subclass, None, object(), object.__new__(TrainingAttempt)):
            with self.subTest(attempt_type=type(attempt)), self.assertRaises(ValueError):
                create_evaluation(attempt=attempt, evaluation_confidence="HIGH", abstain=False)

    def test_03_duck_context_boundary_and_reference_are_rejected(self):
        for path in ("context", "context.knowledge_boundary",
                     "context.knowledge_boundary.learning_map_reference"):
            for replacement in (None, EqualSpoof(), SimpleNamespace):
                attempt = self.make_attempt()
                original = attempt
                for name in path.split("."):
                    original = getattr(original, name)
                value = SimpleNamespace(**vars(original)) if replacement is SimpleNamespace else replacement
                with self.subTest(path=path, replacement=replacement), self.assertRaises(ValueError):
                    self.evaluate(self.tamper(attempt, path, value))

    def test_04_constructor_invalid_tampering_is_rejected(self):
        invalid = (
            ("stage", "S2"), ("stage", "S4"), ("stage", EqualSpoof()),
            ("id", "not-a-uuid"), ("id", str(uuid4()).upper()),
            ("id", "00000000-0000-1000-8000-000000000000"),
            ("id", CallerText(str(uuid4()))),
            ("created_at", datetime.now()),
            ("created_at", datetime.now(timezone(timedelta(hours=1)))),
            ("created_at", "2026-10-02"), ("image_reference", "image.png"),
            ("revision", 0), ("revision", []), ("status", "DRAFT"),
            ("status", CallerText("SUBMITTED")),
            ("user_analysis", "  "), ("user_analysis", ["analysis"]),
            ("user_confidence", True), ("user_confidence", []),
            ("context.market_scenario", ""),
            ("context.observation_task", ["task"]),
            ("context.primary_objective", "\t"),
            ("context.target_concept_id", IMPULSE),
            ("context.training_mode", "PRACTICE"),
            ("context.focus_error_id", " "),
            ("context.knowledge_boundary.stage", "S2"),
            ("context.knowledge_boundary.allowed_concept_ids", frozenset({HIGH})),
            ("context.knowledge_boundary.learned_concept_ids", frozenset({IMPULSE})),
            ("context.knowledge_boundary.learned_concept_ids", frozenset({"UNKNOWN"})),
            ("context.knowledge_boundary.concept_confidence", ((HIGH, "CORE"),)),
            ("context.knowledge_boundary.learning_map_reference.commit", "wrong"),
            ("context.knowledge_boundary.learning_map_reference.path", "wrong"),
            ("context.knowledge_boundary.learning_map_reference.blob", "wrong"),
        )
        for path, value in invalid:
            with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                self.evaluate(self.tamper(self.make_attempt(), path, value))
        attempt = self.make_attempt()
        self.tamper(attempt, "context.training_mode", "FOCUSED")
        with self.assertRaises(ValueError):
            self.evaluate(attempt)

    def test_05_equality_spoofed_error_ids_are_rejected(self):
        for error in (EqualSpoof(), SpoofText("UNKNOWN", "OBS-001"),
                      SpoofText("   ", "OBS-001")):
            self.assert_rejected_error(self.make_attempt(), error)

    def test_06_equality_spoofed_confidence_is_rejected(self):
        for confidence in (EqualSpoof(), SpoofText("UNKNOWN", "HIGH"),
                           SpoofText(" ", "HIGH"), "high", None, 1):
            with self.subTest(confidence_type=type(confidence)), self.assertRaises(ValueError):
                self.evaluate(evaluation_confidence=confidence)

    def test_07_abstain_requires_strict_bool(self):
        for abstain in (0, 1, None, "true", "false", [], EqualSpoof()):
            with self.subTest(abstain=abstain), self.assertRaises(ValueError):
                self.evaluate(abstain=abstain)
        for abstain in (False, True):
            self.assertIs(type(self.evaluate(abstain=abstain).abstain), bool)

    def test_08_mutable_positive_feedback_is_copied(self):
        positives = ["You stated the interval."]
        result = self.evaluate(what_was_correct=positives)
        positives[0] = "Replaced"
        positives.append("Added later")
        self.assertEqual(result.what_was_correct, ("You stated the interval.",))
        self.assertIs(type(result.what_was_correct), tuple)

    def test_09_mutable_contributors_are_copied(self):
        contributors = ["OBS-001"]
        result = self.evaluate(contributors=contributors)
        contributors[0] = "LOC-001"
        contributors.append("UNKNOWN")
        self.assertEqual(result.contributors, ("OBS-001",))
        self.assertEqual(result.skill_signal, "SKL-S1-MARKET-STATE")

    def test_10_all_stored_string_subclasses_become_base_strings(self):
        sources = [CallerText(text) for text in (
            "The interval was stated.", "Separate the high from a structural turn.",
            "OBS-001", "OBS-002", "Describe only what is observable.", "MEDIUM",
        )]
        result = self.evaluate(self.make_attempt(learned=[HIGH, FACT]),
                               what_was_correct=[sources[0]], primary_issue=sources[1],
                               primary_error=sources[2], contributors=[sources[3]],
                               hint=sources[4], evaluation_confidence=sources[5])
        values = (result.attempt_id, *result.what_was_correct, result.primary_issue,
                  result.primary_error, *result.contributors, result.hint,
                  result.skill_signal, result.evaluation_confidence)
        self.assertTrue(all(type(value) is str for value in values))
        self.assertTrue(all(value is not source for value in values for source in sources))

    def test_11_post_call_source_mutation_cannot_change_any_field(self):
        attempt = self.make_attempt(learned=[HIGH, FACT])
        positive = CallerText("You stated the interval.")
        primary = CallerText("OBS-001")
        contributor = CallerText("OBS-002")
        prose = CallerText("Describe the visible evidence.")
        confidence = CallerText("HIGH")
        positives, contributors = [positive], [contributor]
        result = self.evaluate(attempt, what_was_correct=positives, primary_error=primary,
                               contributors=contributors, primary_issue=prose,
                               hint=prose, evaluation_confidence=confidence)
        before = asdict(result)
        positives.clear()
        contributors[:] = ["LOC-001", "UNKNOWN"]
        for source in (positive, primary, contributor, prose, confidence):
            source.marker = ["new mutable state"]
        self.tamper(attempt, "id", str(uuid4()))
        self.tamper(attempt, "user_analysis", "Changed after evaluation")
        self.tamper(attempt, "context.knowledge_boundary.learned_concept_ids", frozenset())
        self.assertEqual(asdict(result), before)

    def test_12_s1_rejects_every_s2_and_s3_formal_error(self):
        for error, stage, _, _ in ERROR_ROWS:
            if stage != "S1":
                self.assert_rejected_error(self.make_attempt(), error)

    def test_13_s2_rejects_every_s3_formal_error(self):
        for error, stage, _, _ in ERROR_ROWS:
            if stage == "S3":
                self.assert_rejected_error(self.make_attempt("S2", [HIGH, IMPULSE]), error)

    def test_14_learned_earlier_stage_error_is_eligible(self):
        for stage in ("S2", "S3"):
            attempt = self.make_attempt(stage, [HIGH])
            for content in ({"primary_error": "OBS-001"}, {"contributors": ["OBS-001"]}):
                with self.subTest(stage=stage, content=content):
                    result = self.evaluate(attempt, **content)
                    self.assertEqual(result.skill_signal, "SKL-S1-MARKET-STATE")

    def test_15_unlearned_support_cannot_authorize_an_error(self):
        for learned in ([HIGH], []):
            self.assert_rejected_error(self.make_attempt(learned=learned), "OBS-002")
        self.assert_rejected_error(self.make_attempt(learned=[]), "OBS-001")

    def test_16_later_learning_cannot_expand_saved_authority(self):
        learned = [HIGH]
        attempt = self.make_attempt(learned=learned)
        before = asdict(attempt)
        learned.extend([FACT, IMPULSE])
        self.assert_rejected_error(attempt, "OBS-002")
        self.assertEqual(asdict(attempt), before)
        self.assertEqual(attempt.context.knowledge_boundary.learned_concept_ids, frozenset({HIGH}))
        self.assertEqual(self.evaluate(attempt, primary_error="OBS-001").primary_error, "OBS-001")

    def test_17_more_than_two_eligible_contributors_are_rejected(self):
        with self.assertRaises(ValueError):
            self.evaluate(self.make_attempt(learned=[HIGH, FACT]),
                          contributors=["OBS-001", "OBS-002", "OBS-004"])

    def test_18_duplicate_contributors_after_normalization_are_rejected(self):
        for contributors in (["OBS-001", "OBS-001"],
                             [CallerText("OBS-001"), CallerText("OBS-001")]):
            with self.subTest(contributors=contributors), self.assertRaises(ValueError):
                self.evaluate(contributors=contributors)

    def test_19_primary_cannot_also_be_a_contributor(self):
        for primary, contributor in (("OBS-001", "OBS-001"),
                                     (CallerText("OBS-001"), CallerText("OBS-001"))):
            with self.subTest(primary_type=type(primary)), self.assertRaises(ValueError):
                self.evaluate(primary_error=primary, contributors=[contributor])

    def test_20_abstention_cannot_include_a_primary_error(self):
        for confidence in ("HIGH", "MEDIUM", "LOW"):
            with self.subTest(confidence=confidence), self.assertRaises(ValueError):
                self.evaluate(primary_error="OBS-001", abstain=True,
                              evaluation_confidence=confidence)

    def test_21_abstention_cannot_include_contributors(self):
        for contributors in (["OBS-001"], ["OBS-001", "OBS-002"]):
            with self.subTest(contributors=contributors), self.assertRaises(ValueError):
                self.evaluate(self.make_attempt(learned=[HIGH, FACT]),
                              contributors=contributors, abstain=True)

    def test_22_low_requires_abstention_and_all_confidences_may_abstain(self):
        with self.assertRaises(ValueError):
            self.evaluate(evaluation_confidence="LOW", abstain=False)
        for confidence in ("HIGH", "MEDIUM", "LOW"):
            result = self.evaluate(evaluation_confidence=confidence, abstain=True,
                                   what_was_correct=["You stated the interval."],
                                   primary_issue="The submitted evidence is insufficient.")
            self.assertTrue(result.abstain)
            self.assertIsNone(result.primary_error)
            self.assertEqual(result.contributors, ())
            self.assertEqual(result.what_was_correct, ("You stated the interval.",))

    def test_23_unknown_or_malformed_formal_errors_are_rejected(self):
        for error in ("UNKNOWN", "OBS-003", "STR-008", "LOC-007", "OBS-001,OBS-002",
                      "obs-001", " OBS-001 ", "", " \t", None, 1, ["OBS-001"]):
            if error is None:
                with self.assertRaises(ValueError):
                    self.evaluate(contributors=[error])
            else:
                self.assert_rejected_error(self.make_attempt(), error)

    def test_24_correct_no_error_does_not_automatically_abstain(self):
        for confidence in ("HIGH", "MEDIUM"):
            result = self.evaluate(evaluation_confidence=confidence,
                                   what_was_correct=["The high was described in its interval."])
            self.assertFalse(result.abstain)
            self.assertIsNone(result.primary_error)
            self.assertEqual(result.contributors, ())

    def test_25_exactly_one_primary_error_is_supported(self):
        result = self.evaluate(primary_error="OBS-001")
        self.assertEqual(result.primary_error, "OBS-001")
        self.assertIs(type(result.primary_error), str)
        self.assertEqual(result.skill_signal, "SKL-S1-MARKET-STATE")
        for primary in (["OBS-001", "OBS-002"], ("OBS-001", "OBS-002")):
            with self.assertRaises(ValueError):
                self.evaluate(primary_error=primary)

    def test_26_zero_contributors_on_primary_correct_and_abstain_paths(self):
        for content in ({"primary_error": "OBS-001"}, {}, {"abstain": True}):
            self.assertEqual(self.evaluate(**content).contributors, ())

    def test_27_one_contributor_with_or_without_primary(self):
        attempt = self.make_attempt(learned=[HIGH, FACT])
        for primary in (None, "OBS-001"):
            result = self.evaluate(attempt, primary_error=primary, contributors=["OBS-002"])
            self.assertEqual(result.contributors, ("OBS-002",))
            self.assertEqual(result.primary_error, primary)

    def test_28_two_contributors_preserve_order_with_or_without_primary(self):
        attempt = self.make_attempt(learned=[HIGH, FACT])
        for primary in (None, "OBS-001"):
            result = self.evaluate(attempt, primary_error=primary,
                                   contributors=["OBS-004", "OBS-002"])
            self.assertEqual(result.contributors, ("OBS-004", "OBS-002"))
            self.assertEqual(result.primary_error, primary)

    def test_29_skill_derivation_primary_first_contributor_and_stage_fallback(self):
        attempt = self.make_attempt("S3", [HIGH, IMPULSE, LOCATION])
        cases = (
            ("OBS-001", ["STR-003", "LOC-001"], "SKL-S1-MARKET-STATE"),
            ("LOC-001", ["STR-003", "OBS-001"], "SKL-S3-MARKET-LOCATION"),
            (None, ["STR-003", "OBS-001"], "SKL-S2-STRUCTURE-MOVEMENT"),
            (None, ["OBS-001", "STR-003"], "SKL-S1-MARKET-STATE"),
        )
        for primary, contributors, expected in cases:
            with self.subTest(primary=primary, contributors=contributors):
                self.assertEqual(self.evaluate(attempt, primary_error=primary,
                                               contributors=contributors).skill_signal, expected)
        for stage, expected in SKILLS.items():
            for abstain in (False, True):
                with self.subTest(stage=stage, abstain=abstain):
                    self.assertEqual(self.evaluate(self.make_attempt(stage, []),
                                                   abstain=abstain).skill_signal, expected)

    def test_30_initial_analysis_context_and_boundary_unchanged(self):
        attempt = self.make_attempt()
        context, boundary, analysis = attempt.context, attempt.context.knowledge_boundary, attempt.user_analysis
        before = asdict(attempt)
        self.evaluate(attempt, primary_error="OBS-001")
        with self.assertRaises(ValueError):
            self.evaluate(attempt, primary_error="OBS-002")
        self.assertEqual(asdict(attempt), before)
        self.assertIs(attempt.context, context)
        self.assertIs(attempt.context.knowledge_boundary, boundary)
        self.assertIs(attempt.user_analysis, analysis)
        self.assertEqual(attempt.user_analysis, "  The high is observable in the chosen interval.\n")

    def test_31_no_future_market_outcome_argument_or_dependency(self):
        signature = inspect.signature(create_evaluation)
        self.assertFalse(any(p.kind is inspect.Parameter.VAR_KEYWORD
                             for p in signature.parameters.values()))
        for name in ("later_price_movement", "future_candles", "realized_pnl",
                     "realized_profit_loss", "trade_result", "prediction_result",
                     "later_market_outcome", "prediction", "trading_signal"):
            with self.subTest(name=name), self.assertRaises(TypeError):
                self.evaluate(**{name: object()})
        # Diagnostic feedback is fully determined without any outcome inputs.
        attempt = self.make_attempt()
        self.assertEqual(self.evaluate(attempt, primary_error="OBS-001"),
                         self.evaluate(attempt, primary_error="OBS-001"))

    def test_32_approved_error_tokens_cannot_be_hidden_in_diagnostic_prose(self):
        self.assertEqual(len(ERROR_ROWS), 19)
        for error, _, _, _ in ERROR_ROWS:
            for field in ("primary_issue", "hint"):
                for text in (error, f"Consider ({error}).", f"{error}; OBS-001",
                             SpoofText(f"Review [{error}]", "Apparently harmless prose")):
                    for abstain in (False, True):
                        with self.subTest(error=error, field=field, abstain=abstain), self.assertRaises(ValueError):
                            self.evaluate(abstain=abstain, **{field: text})

    def test_33_public_construction_and_replace_cannot_bypass_factory(self):
        valid = self.evaluate(primary_error="OBS-001")
        values = asdict(valid)
        calls = (
            lambda: Evaluation(),
            lambda: Evaluation(*[values[name] for name in NINE_FIELDS]),
            lambda: Evaluation(**values),
            lambda: Evaluation(primary_error=["OBS-001", "LOC-001"], abstain=True),
            lambda: Evaluation(validation_token=object()),
            lambda: Evaluation.__new__(Evaluation),
            lambda: replace(valid),
            lambda: replace(valid, primary_error="LOC-001"),
            lambda: replace(valid, abstain=True),
        )
        for number, call in enumerate(calls):
            with self.subTest(constructor=number), self.assertRaises(TypeError):
                call()
        self.assertEqual(tuple(f.name for f in fields(Evaluation)), NINE_FIELDS)
        self.assertEqual(Evaluation.__slots__, NINE_FIELDS)
        self.assertEqual(tuple(values), NINE_FIELDS)
        self.assertFalse(hasattr(valid, "__dict__"))
        self.assertFalse(Evaluation.__dataclass_params__.init)
        self.assertTrue(Evaluation.__dataclass_params__.frozen)
        for name in NINE_FIELDS:
            with self.subTest(field=name), self.assertRaises(FrozenInstanceError):
                setattr(valid, name, None)
            with self.subTest(deleted_field=name), self.assertRaises(FrozenInstanceError):
                delattr(valid, name)

    def test_no_authority_or_diagnostic_scope_override_parameters(self):
        self.assertEqual(set(inspect.signature(create_evaluation).parameters), {
            "attempt", "what_was_correct", "primary_issue", "primary_error",
            "contributors", "hint", "evaluation_confidence", "abstain",
        })
        for name in ("skill_signal", "target", "target_concept_id", "objective",
                     "primary_objective", "observation_task", "stage", "context",
                     "knowledge_boundary", "allowed_concept_ids", "learned_concept_ids",
                     "error_to_concept", "error_concept_mapping", "mapping",
                     "errors", "formal_errors", "primary_errors", "authority_token",
                     "validation_token"):
            with self.subTest(name=name), self.assertRaises(TypeError):
                self.evaluate(**{name: object()})

    def test_package_exports_only_the_record_and_validated_factory(self):
        self.assertEqual(set(evaluation.__all__), {"Evaluation", "create_evaluation"})
        public_callables = {name for name in vars(evaluation)
                            if not name.startswith("_") and callable(getattr(evaluation, name))}
        self.assertEqual(public_callables, {"Evaluation", "create_evaluation"})

    def test_supplied_diagnostic_text_is_nonempty_and_string_only(self):
        for value in ("", " \t\n", None, [], 1, EqualSpoof(), SpoofText(" ", "Nonempty")):
            with self.subTest(positive=value), self.assertRaises(ValueError):
                self.evaluate(what_was_correct=[value])
        for field in ("primary_issue", "hint"):
            for value in ("", " \t\n", [], 1, EqualSpoof(), SpoofText(" ", "Nonempty")):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.evaluate(**{field: value})
            self.assertIsNone(getattr(self.evaluate(**{field: None}), field))

    def test_diagnostic_collections_require_ordered_list_or_tuple_members(self):
        for field in ("what_was_correct", "contributors"):
            for value in (None, "OBS-001", b"OBS-001", bytearray(b"OBS-001"),
                          1, {"OBS-001"}, {"OBS-001": "value"}, [["OBS-001"]],
                          [EqualSpoof()], [b"OBS-001"]):
                with self.subTest(field=field, value_type=type(value)), self.assertRaises(ValueError):
                    self.evaluate(**{field: value})

    def test_nested_mutable_boundary_aliases_are_rejected(self):
        for path in ("allowed_concept_ids", "learned_concept_ids", "concept_confidence"):
            attempt = self.make_attempt()
            boundary = attempt.context.knowledge_boundary
            value = list(getattr(boundary, path))
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.evaluate(self.tamper(attempt, "context.knowledge_boundary." + path, value))
        attempt = self.make_attempt()
        pairs = tuple(list(pair) for pair in attempt.context.knowledge_boundary.concept_confidence)
        with self.assertRaises(ValueError):
            self.evaluate(self.tamper(attempt, "context.knowledge_boundary.concept_confidence", pairs))

    def test_tampered_core_confidence_cannot_spoof_canonical_authority(self):
        for confidence in ("CONTEXTUAL", "CONTESTED", "UNKNOWN", EqualSpoof(),
                           SpoofText("UNKNOWN", "CORE")):
            attempt = self.make_attempt()
            pairs = tuple((concept, confidence if concept == HIGH else value)
                          for concept, value in attempt.context.knowledge_boundary.concept_confidence)
            with self.subTest(confidence_type=type(confidence)), self.assertRaises(ValueError):
                self.evaluate(self.tamper(attempt, "context.knowledge_boundary.concept_confidence", pairs),
                              primary_error="OBS-001")

    def test_reference_scalar_equality_spoof_cannot_pass_reconstruction(self):
        canonical = {
            "commit": "65cd6969e8ccf890d6e51b07fd7436564bf70421",
            "path": "spec/learning_map/LEARNING_MAP_SPEC.md",
            "blob": "726b35db8409ea03cbec33c916db7374e6724e03",
        }
        for field, expected in canonical.items():
            for value in (EqualSpoof(), SpoofText("invalid", expected), [], None):
                attempt = self.make_attempt()
                with self.subTest(field=field, value_type=type(value)), self.assertRaises(ValueError):
                    self.evaluate(self.tamper(attempt,
                                              "context.knowledge_boundary.learning_map_reference." + field,
                                              value))

    def test_nested_concept_and_stage_equality_spoofs_are_rejected(self):
        for path, value in (
            ("stage", SpoofText("S8", "S1")),
            ("context.knowledge_boundary.stage", SpoofText("S8", "S1")),
            ("context.target_concept_id", SpoofText("UNKNOWN", HIGH)),
            ("context.training_mode", SpoofText("UNKNOWN", "FORMAL")),
            ("context.knowledge_boundary.learned_concept_ids", frozenset({SpoofText("UNKNOWN", HIGH)})),
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.evaluate(self.tamper(self.make_attempt(), path, value))
        attempt = self.make_attempt()
        allowed = frozenset(SpoofText("UNKNOWN", concept) if concept == HIGH else concept
                            for concept in attempt.context.knowledge_boundary.allowed_concept_ids)
        with self.assertRaises(ValueError):
            self.evaluate(self.tamper(attempt, "context.knowledge_boundary.allowed_concept_ids", allowed))

    def test_valid_canonical_nested_text_subclasses_are_copied_without_input_mutation(self):
        attempt = self.make_attempt()
        self.tamper(attempt, "stage", CallerText("S1"))
        self.tamper(attempt, "user_analysis", CallerText(attempt.user_analysis))
        self.tamper(attempt, "user_confidence", CallerText("MEDIUM"))
        context = attempt.context
        for field in ("market_scenario", "observation_task", "primary_objective",
                      "target_concept_id", "training_mode"):
            self.tamper(attempt, "context." + field, CallerText(getattr(context, field)))
        boundary = context.knowledge_boundary
        self.tamper(attempt, "context.knowledge_boundary.stage", CallerText("S1"))
        self.tamper(attempt, "context.knowledge_boundary.allowed_concept_ids",
                    frozenset(CallerText(c) for c in boundary.allowed_concept_ids))
        self.tamper(attempt, "context.knowledge_boundary.learned_concept_ids", frozenset({CallerText(HIGH)}))
        self.tamper(attempt, "context.knowledge_boundary.concept_confidence",
                    tuple((CallerText(c), CallerText(v)) for c, v in boundary.concept_confidence))
        reference = boundary.learning_map_reference
        for field in ("commit", "path", "blob"):
            self.tamper(attempt, "context.knowledge_boundary.learning_map_reference." + field,
                        CallerText(getattr(reference, field)))
        before = asdict(attempt)
        self.assertEqual(self.evaluate(attempt, primary_error="OBS-001").primary_error, "OBS-001")
        self.assertEqual(asdict(attempt), before)
        self.assertIs(type(attempt.user_analysis), CallerText)

    def test_every_published_mapping_supports_only_its_mapped_learned_concepts(self):
        self.assertEqual(len(ERROR_ROWS), 19)
        for error, stage, skill, mapped in ERROR_ROWS:
            allowed = self.make_attempt(stage, []).context.knowledge_boundary.allowed_concept_ids
            self.assertTrue(set(mapped) <= allowed)
            self.assertEqual(skill, SKILLS[stage])
            for concept in sorted(allowed):
                attempt = self.make_attempt(stage, [concept])
                for content in ({"primary_error": error}, {"contributors": [error]}):
                    with self.subTest(error=error, learned=concept, content=content):
                        if concept in mapped:
                            self.assertEqual(self.evaluate(attempt, **content).skill_signal, skill)
                        else:
                            with self.assertRaises(ValueError):
                                self.evaluate(attempt, **content)

    def test_later_map_reference_cannot_rewrite_the_submission_boundary(self):
        for path, value in (("commit", "f" * 40), ("blob", "f" * 40),
                            ("path", "spec/learning_map/FUTURE_MAP.md")):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.evaluate(self.tamper(self.make_attempt(),
                                          "context.knowledge_boundary.learning_map_reference." + path, value))

    def test_output_contains_only_immutable_values_and_has_no_nested_authority(self):
        result = self.evaluate(self.make_attempt(learned=[HIGH, FACT]),
                               what_was_correct=["The interval was stated."],
                               primary_error="OBS-001", contributors=["OBS-002"],
                               hint="Describe the visible evidence.")
        self.assertEqual(tuple(asdict(result)), NINE_FIELDS)
        for value in asdict(result).values():
            self.assertIn(type(value), (str, tuple, bool, type(None)))
            if type(value) is tuple:
                self.assertTrue(all(type(item) is str for item in value))
        with self.assertRaises(TypeError):
            result.what_was_correct[0] = "changed"
        with self.assertRaises(TypeError):
            result.contributors[0] = "LOC-001"

    def test_formal_and_focused_attempts_share_the_same_evaluation_contract(self):
        formal = self.make_attempt()
        focused = self.make_attempt(training_mode="FOCUSED", focus_error_id="OBS-001")
        for attempt in (formal, focused):
            self.assertIs(type(self.evaluate(attempt, primary_error="OBS-001")), Evaluation)
            self.assertEqual(self.evaluate(attempt).skill_signal, "SKL-S1-MARKET-STATE")

    def test_post002_same_stage_expansion_rejected_in_both_error_channels(self):
        original = self.make_attempt(learned=[HIGH])
        later = self.make_attempt(learned=[HIGH, FACT])
        before = asdict(original)
        values = {field.name: getattr(original, field.name) for field in fields(original)}
        for channel in ("primary_error", "contributors"):
            diagnostics = {channel: "OBS-002" if channel == "primary_error" else ["OBS-002"]}
            with self.subTest(channel=channel), self.assertRaises(ValueError):
                self.evaluate(original, **diagnostics)
            for reconstruct in (lambda: TrainingAttempt(**{**values, "context": later.context}),
                                lambda: replace(original, context=later.context)):
                with self.subTest(channel=channel, route=reconstruct), self.assertRaises(TypeError):
                    reconstruct()
                self.assertEqual(asdict(original), before)
            self.assertEqual(self.evaluate(later, **diagnostics).skill_signal, SKILLS["S1"])

    def test_post002_s3_transplant_rejected_in_both_error_channels(self):
        original = self.make_attempt(learned=[HIGH])
        later = self.make_attempt("S3", [LOCATION])
        before = asdict(original)
        values = {field.name: getattr(original, field.name) for field in fields(original)}
        for channel in ("primary_error", "contributors"):
            diagnostics = {channel: "LOC-001" if channel == "primary_error" else ["LOC-001"]}
            with self.subTest(channel=channel), self.assertRaises(ValueError):
                self.evaluate(original, **diagnostics)
            for reconstruct in (lambda: TrainingAttempt(**{**values, "stage": "S3", "context": later.context}),
                                lambda: replace(original, stage="S3", context=later.context)):
                with self.subTest(channel=channel, route=reconstruct), self.assertRaises(TypeError):
                    reconstruct()
                self.assertEqual(asdict(original), before)
            self.assertEqual(self.evaluate(later, **diagnostics).skill_signal, SKILLS["S3"])

    def test_post002_later_learning_requires_a_fresh_factory_submission(self):
        learned = [HIGH]
        original = self.make_attempt(learned=learned)
        before = asdict(original)
        learned.append(FACT)
        later = self.make_attempt(learned=learned)
        self.assertNotEqual(later.id, original.id)
        self.assertEqual(original.context.knowledge_boundary.learned_concept_ids, frozenset({HIGH}))
        self.assertEqual(later.context.knowledge_boundary.learned_concept_ids, frozenset({HIGH, FACT}))
        for diagnostics in ({"primary_error": "OBS-002"}, {"contributors": ["OBS-002"]}):
            with self.subTest(diagnostics=diagnostics), self.assertRaises(ValueError):
                self.evaluate(original, **diagnostics)
            self.assertEqual(self.evaluate(later, **diagnostics).attempt_id, later.id)
        self.assertEqual(asdict(original), before)

    def test_setstate_rejects_even_valid_state_without_changing_any_field(self):
        result = self.evaluate(self.make_attempt(learned=[HIGH, FACT]),
                               what_was_correct=["The interval was stated."],
                               primary_issue="Separate observation from interpretation.",
                               primary_error="OBS-001", contributors=["OBS-002"],
                               hint="Describe the visible evidence.")
        before = asdict(result)
        original_values = tuple(getattr(result, name) for name in NINE_FIELDS)
        for state in (list(original_values), original_values):
            with self.subTest(state_type=type(state)), self.assertRaisesRegex(TypeError, "not supported"):
                result.__setstate__(state)
            self.assertEqual(asdict(result), before)
            for name, value in zip(NINE_FIELDS, original_values):
                self.assertIs(getattr(result, name), value)

    def test_setstate_hostile_injections_leave_all_nine_fields_unchanged(self):
        cases = (
            ("wrong_attempt_id", {"attempt_id": "wrong-attempt-id"}),
            ("future_stage_primary", {"primary_error": "LOC-001"}),
            ("future_stage_contributor", {"contributors": ["LOC-001"]}),
            ("unlearned_primary", {"primary_error": "OBS-002"}),
            ("unlearned_contributor", {"contributors": ["OBS-002"]}),
            ("unknown_primary", {"primary_error": "UNKNOWN"}),
            ("unknown_contributor", {"contributors": ["UNKNOWN"]}),
            ("too_many_contributors", {"contributors": ["OBS-002", "OBS-004", "STR-001"]}),
            ("duplicate_contributors", {"contributors": ["OBS-002", "OBS-002"]}),
            ("primary_contributor_overlap", {"contributors": ["OBS-001"]}),
            ("issue_error_id", {"primary_issue": "Consider OBS-001."}),
            ("hint_error_id", {"hint": "Review LOC-001."}),
            ("caller_skill", {"skill_signal": "SKL-S8-CALLER-OVERRIDE"}),
            ("non_bool_abstain", {"abstain": 1}),
            ("low_with_errors", {"evaluation_confidence": "LOW", "abstain": True}),
            ("low_without_abstention", {"evaluation_confidence": "LOW", "abstain": False}),
            ("mutable_positives", {"what_was_correct": ["Caller positive"]}),
            ("mutable_contributors", {"primary_error": None, "contributors": ["OBS-001"]}),
        )
        for label, changes in cases:
            with self.subTest(case=label):
                result = self.evaluate(what_was_correct=["Original positive"],
                                       primary_issue="Original issue", primary_error="OBS-001",
                                       hint="Original hint")
                before = asdict(result)
                state = [changes.get(name, getattr(result, name)) for name in NINE_FIELDS]
                with self.assertRaisesRegex(TypeError, "not supported"):
                    result.__setstate__(state)
                self.assertEqual(asdict(result), before)
                for value in changes.values():
                    if isinstance(value, list):
                        value[:] = ["Caller changed after rejection"]
                self.assertEqual(asdict(result), before)

    def test_setstate_rejects_partial_and_malformed_state_before_any_write(self):
        for state in (["wrong-attempt-id"], [], None, {"attempt_id": "wrong-attempt-id"},
                      ["wrong-attempt-id"] * 10):
            with self.subTest(state=state):
                result = self.evaluate(primary_error="OBS-001")
                before = asdict(result)
                with self.assertRaisesRegex(TypeError, "not supported"):
                    result.__setstate__(state)
                self.assertEqual(asdict(result), before)

    def test_setstate_rejection_does_not_iterate_caller_controlled_state(self):
        inspected = []

        def partial_state():
            inspected.append("iterated")
            yield "wrong-attempt-id"

        result = self.evaluate(primary_error="OBS-001")
        before = asdict(result)
        with self.assertRaisesRegex(TypeError, "not supported"):
            result.__setstate__(partial_state())
        self.assertEqual(inspected, [])
        self.assertEqual(asdict(result), before)

    def test_setstate_cannot_retain_mutable_collection_aliases(self):
        result = self.evaluate(self.make_attempt(learned=[HIGH, FACT]),
                               what_was_correct=["Original positive"],
                               primary_error="OBS-001", contributors=["OBS-002"])
        before = asdict(result)
        positives, contributors = ["Caller positive"], ["OBS-002"]
        state = [getattr(result, name) for name in NINE_FIELDS]
        state[1], state[4] = positives, contributors
        with self.assertRaisesRegex(TypeError, "not supported"):
            result.__setstate__(state)
        self.assertEqual(asdict(result), before)
        self.assertIsNot(result.what_was_correct, positives)
        self.assertIsNot(result.contributors, contributors)
        positives.append("Caller changed later")
        contributors[:] = ["LOC-001", "UNKNOWN", "OBS-004"]
        self.assertEqual(asdict(result), before)

    def test_pickle_dumps_rejects_every_protocol_and_preserves_original(self):
        result = self.evaluate(primary_error="OBS-001")
        before = asdict(result)
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.subTest(protocol=protocol), self.assertRaisesRegex(TypeError, "not supported"):
                pickle.dumps(result, protocol=protocol)
            self.assertEqual(asdict(result), before)

    def test_public_reduce_rejects_without_changing_original(self):
        result = self.evaluate(primary_error="OBS-001")
        before = asdict(result)
        with self.assertRaisesRegex(TypeError, "not supported"):
            result.__reduce__()
        self.assertEqual(asdict(result), before)

    def test_public_reduce_ex_rejects_every_protocol_without_changing_original(self):
        result = self.evaluate(primary_error="OBS-001")
        before = asdict(result)
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.subTest(protocol=protocol), self.assertRaisesRegex(TypeError, "not supported"):
                result.__reduce_ex__(protocol)
            self.assertEqual(asdict(result), before)

    def test_historical_pickle_protocols_0_and_1_cannot_reconstruct_future_stage_error(self):
        result = self.evaluate(primary_error="OBS-001")
        before = asdict(result)
        self.assertEqual(tuple(protocol for protocol, _ in HISTORICAL_PICKLE_PAYLOADS), (0, 1))
        for protocol, payload in HISTORICAL_PICKLE_PAYLOADS:
            self.assertIn(b"OBS-001", payload)
            hostile = payload.replace(b"OBS-001", b"LOC-001")
            for label, candidate in (("original", payload), ("future_stage_error", hostile)):
                with self.subTest(protocol=protocol, payload=label), self.assertRaisesRegex(TypeError, "not supported"):
                    pickle.loads(candidate)
                self.assertEqual(asdict(result), before)


if __name__ == "__main__":
    unittest.main()
