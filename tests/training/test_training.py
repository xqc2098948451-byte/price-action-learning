import unittest
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from price_action_learning.training import (
    KnowledgeBoundary,
    LearningMapReference,
    TrainingAttempt,
    TrainingContext,
    create_training_attempt,
)


S1 = "CON-S1-HIGH"
S2 = "CON-S2-IMPULSE"
S3 = "CON-S3-RANGE-HIGH"


class TrainingAttemptTests(unittest.TestCase):
    def make_attempt(self, **overrides):
        values = {
            "stage": "S1",
            "market_scenario": "An observable sequence of swing highs and lows",
            "observation_task": "Identify the observed high",
            "primary_objective": "Describe the high before interpreting it",
            "target_concept_id": S1,
            "training_mode": "FORMAL",
            "learned_concept_ids": {S1},
            "user_analysis": "The chosen interval has a visible high.",
            "user_confidence": "MEDIUM",
        }
        values.update(overrides)
        return create_training_attempt(**values)

    def make_direct_context(self, boundary):
        return TrainingContext(
            market_scenario="Visible swing highs and lows",
            observation_task="Identify the high",
            primary_objective="Describe the high",
            target_concept_id=S1,
            training_mode="FORMAL",
            focus_error_id=None,
            knowledge_boundary=boundary,
        )

    def make_direct_attempt(self, **overrides):
        source = self.make_attempt()
        values = {field.name: getattr(source, field.name) for field in fields(TrainingAttempt)}
        values.update(overrides)
        return TrainingAttempt(**values)

    def test_direct_context_copies_mutable_boundary_into_immutable_canonical_form(self):
        canonical = self.make_attempt().context.knowledge_boundary
        source = SimpleNamespace(
            stage="S1",
            allowed_concept_ids=list(canonical.allowed_concept_ids),
            learned_concept_ids=[S1],
            concept_confidence=[list(pair) for pair in canonical.concept_confidence],
            learning_map_reference=canonical.learning_map_reference,
        )
        context = self.make_direct_context(source)
        source.learned_concept_ids.append(S2)
        source.stage = "S2"

        self.assertIs(type(context.knowledge_boundary), KnowledgeBoundary)
        self.assertIsNot(context.knowledge_boundary, source)
        self.assertEqual(context.knowledge_boundary.stage, "S1")
        self.assertEqual(context.knowledge_boundary.learned_concept_ids, frozenset({S1}))
        self.assertIs(type(context.knowledge_boundary.allowed_concept_ids), frozenset)
        self.assertIs(type(context.knowledge_boundary.concept_confidence), tuple)
        with self.assertRaises(FrozenInstanceError):
            context.knowledge_boundary.stage = "S2"

    def test_direct_context_copies_existing_canonical_boundary(self):
        source = self.make_attempt().context.knowledge_boundary
        context = self.make_direct_context(source)
        self.assertIs(type(context.knowledge_boundary), KnowledgeBoundary)
        self.assertIsNot(context.knowledge_boundary, source)
        self.assertEqual(context.knowledge_boundary, source)

    def test_direct_context_rejects_malformed_and_noncanonical_boundaries(self):
        canonical = self.make_attempt().context.knowledge_boundary
        valid = vars(canonical).copy()
        invalid = (
            None,
            SimpleNamespace(stage="S1"),
            SimpleNamespace(**{**valid, "allowed_concept_ids": {S1, S2}}),
            SimpleNamespace(**{**valid, "learned_concept_ids": {S2}}),
            SimpleNamespace(**{**valid, "concept_confidence": ((S1, "CORE"),)}),
            SimpleNamespace(**{**valid, "learning_map_reference": None}),
        )
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.make_direct_context(source)

    def test_direct_boundary_does_not_retain_caller_owned_reference(self):
        source = self.make_attempt().context.knowledge_boundary
        reference = LearningMapReference(
            commit="65cd6969e8ccf890d6e51b07fd7436564bf70421",
            path="spec/learning_map/LEARNING_MAP_SPEC.md",
            blob="726b35db8409ea03cbec33c916db7374e6724e03",
        )
        boundary = KnowledgeBoundary(
            stage=source.stage,
            allowed_concept_ids=source.allowed_concept_ids,
            learned_concept_ids=source.learned_concept_ids,
            concept_confidence=source.concept_confidence,
            learning_map_reference=reference,
        )
        context = self.make_direct_context(boundary)
        object.__setattr__(reference, "commit", "changed-after-submission")
        self.assertIsNot(boundary.learning_map_reference, reference)
        self.assertIsNot(boundary.learning_map_reference, source.learning_map_reference)
        self.assertIs(type(boundary.learning_map_reference), LearningMapReference)
        self.assertEqual(boundary.learning_map_reference.commit,
                         "65cd6969e8ccf890d6e51b07fd7436564bf70421")
        self.assertEqual(context.knowledge_boundary.learning_map_reference.commit,
                         "65cd6969e8ccf890d6e51b07fd7436564bf70421")

    def test_direct_boundary_rejects_spoofed_and_noncanonical_reference(self):
        class EqualSpoof:
            def __eq__(self, other):
                return True

        source = self.make_attempt().context.knowledge_boundary
        invalid = (
            None,
            SimpleNamespace(commit="65cd6969e8ccf890d6e51b07fd7436564bf70421",
                            path="spec/learning_map/LEARNING_MAP_SPEC.md",
                            blob="726b35db8409ea03cbec33c916db7374e6724e03"),
            EqualSpoof(),
            LearningMapReference(commit="wrong", path="spec/learning_map/LEARNING_MAP_SPEC.md",
                                 blob="726b35db8409ea03cbec33c916db7374e6724e03"),
        )
        for reference in invalid:
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                KnowledgeBoundary(
                    stage=source.stage,
                    allowed_concept_ids=source.allowed_concept_ids,
                    learned_concept_ids=source.learned_concept_ids,
                    concept_confidence=source.concept_confidence,
                    learning_map_reference=reference,
                )

    def test_direct_boundary_stores_canonical_concept_ids(self):
        class CallerConcept(str):
            pass

        source = self.make_attempt().context.knowledge_boundary
        learned = CallerConcept(S1)
        boundary = KnowledgeBoundary(
            stage="S1",
            allowed_concept_ids={CallerConcept(concept) for concept in source.allowed_concept_ids},
            learned_concept_ids={learned},
            concept_confidence=source.concept_confidence,
            learning_map_reference=source.learning_map_reference,
        )
        self.assertTrue(all(type(concept) is str for concept in boundary.allowed_concept_ids))
        self.assertTrue(all(type(concept) is str for concept in boundary.learned_concept_ids))
        self.assertIsNot(next(iter(boundary.learned_concept_ids)), learned)

    def test_direct_attempt_accepts_matching_stage(self):
        context = self.make_direct_context(self.make_attempt().context.knowledge_boundary)
        attempt = TrainingAttempt(
            id=str(uuid4()), created_at=datetime.now(timezone.utc), stage="S1",
            image_reference=None, user_analysis="A high is visible.",
            user_confidence=None, revision=None, status="SUBMITTED", context=context,
        )
        self.assertEqual(attempt.stage, attempt.context.knowledge_boundary.stage)

    def test_direct_attempt_copies_context_before_source_mutation(self):
        source = self.make_attempt().context
        attempt = self.make_direct_attempt(context=source)
        object.__setattr__(source, "market_scenario", "changed-after-submission")
        self.assertIsNot(attempt.context, source)
        self.assertEqual(attempt.context.market_scenario,
                         "An observable sequence of swing highs and lows")

    def test_direct_attempt_stores_canonical_context_text(self):
        class CallerText(str):
            pass

        source = self.make_attempt().context
        context = TrainingContext(
            market_scenario=CallerText("Visible swing highs and lows"),
            observation_task=source.observation_task,
            primary_objective=source.primary_objective,
            target_concept_id=source.target_concept_id,
            training_mode=source.training_mode,
            focus_error_id=source.focus_error_id,
            knowledge_boundary=source.knowledge_boundary,
        )
        attempt = self.make_direct_attempt(context=context)
        self.assertIs(type(attempt.context.market_scenario), str)
        self.assertEqual(attempt.context.market_scenario, "Visible swing highs and lows")

    def test_direct_context_rejects_empty_text_subclass_with_spoofed_strip(self):
        class EmptySpoof(str):
            def strip(self):
                return "pretend nonempty"

        source = self.make_attempt().context
        with self.assertRaises(ValueError):
            TrainingContext(
                market_scenario=EmptySpoof(""),
                observation_task=source.observation_task,
                primary_objective=source.primary_objective,
                target_concept_id=source.target_concept_id,
                training_mode=source.training_mode,
                focus_error_id=source.focus_error_id,
                knowledge_boundary=source.knowledge_boundary,
            )

    def test_direct_attempt_rejects_duck_context_and_mutable_analysis(self):
        source = self.make_attempt().context
        with self.assertRaises(ValueError):
            self.make_direct_attempt(context=SimpleNamespace(**vars(source)))
        with self.assertRaises(ValueError):
            self.make_direct_attempt(user_analysis=["Initial analysis"])

    def test_direct_attempt_normalizes_caller_owned_scalar_subclasses(self):
        class MutableText(str):
            pass

        analysis = MutableText("Initial analysis")
        confidence = MutableText("MEDIUM")
        attempt = self.make_direct_attempt(user_analysis=analysis,
                                           user_confidence=confidence)
        analysis.marker = "changed"
        confidence.marker = "changed"
        self.assertIs(type(attempt.user_analysis), str)
        self.assertIs(type(attempt.user_confidence), str)
        self.assertIsNot(attempt.user_analysis, analysis)
        self.assertIsNot(attempt.user_confidence, confidence)
        self.assertEqual(attempt.user_analysis, "Initial analysis")
        self.assertEqual(attempt.user_confidence, "MEDIUM")

    def test_direct_attempt_rejects_stage_equality_spoof(self):
        class EqualStage:
            def __eq__(self, other):
                return True

        with self.assertRaises(ValueError):
            self.make_direct_attempt(stage=EqualStage())

    def test_direct_attempt_enforces_initial_submission_fields(self):
        invalid = (
            {"image_reference": "image.png"},
            {"revision": 0},
            {"status": "DRAFT"},
            {"id": "direct-attempt"},
            {"id": str(uuid4()).upper()},
            {"id": "00000000-0000-1000-8000-000000000000"},
            {"created_at": datetime.now()},
            {"created_at": datetime.now(timezone(timedelta(hours=1)))},
            {"user_confidence": True},
            {"user_confidence": []},
        )
        for override in invalid:
            with self.subTest(override=override), self.assertRaises(ValueError):
                self.make_direct_attempt(**override)

    def test_direct_attempt_rejects_mismatching_stage(self):
        context = self.make_direct_context(self.make_attempt().context.knowledge_boundary)
        with self.assertRaisesRegex(ValueError, "stage must match context.knowledge_boundary.stage"):
            TrainingAttempt(
                id=str(uuid4()), created_at=datetime.now(timezone.utc), stage="S2",
                image_reference=None, user_analysis="A high is visible.",
                user_confidence=None, revision=None, status="SUBMITTED", context=context,
            )

    def test_formal_creation_uses_shared_record_and_submission_defaults(self):
        before = datetime.now(timezone.utc)
        attempt = self.make_attempt()
        after = datetime.now(timezone.utc)
        self.assertIs(type(attempt), TrainingAttempt)
        self.assertEqual(
            {field.name for field in fields(TrainingAttempt)},
            {"id", "created_at", "stage", "image_reference", "user_analysis",
             "user_confidence", "revision", "status", "context"},
        )
        self.assertTrue(attempt.id)
        self.assertLessEqual(before, attempt.created_at)
        self.assertLessEqual(attempt.created_at, after)
        self.assertEqual(attempt.stage, "S1")
        self.assertIsNone(attempt.image_reference)
        self.assertEqual(attempt.user_analysis, "The chosen interval has a visible high.")
        self.assertEqual(attempt.user_confidence, "MEDIUM")
        self.assertIsNone(attempt.revision)
        self.assertEqual(attempt.status, "SUBMITTED")
        self.assertEqual(attempt.context.training_mode, "FORMAL")
        self.assertIsNone(attempt.context.focus_error_id)

    def test_each_creation_gets_a_unique_id(self):
        self.assertNotEqual(self.make_attempt().id, self.make_attempt().id)

    def test_focused_uses_same_creation_api_and_record(self):
        attempt = self.make_attempt(training_mode="FOCUSED", focus_error_id="OBS-001")
        self.assertIs(type(attempt), TrainingAttempt)
        self.assertEqual(attempt.context.training_mode, "FOCUSED")
        self.assertEqual(attempt.context.focus_error_id, "OBS-001")

    def test_focused_requires_nonempty_error_id(self):
        for value in (None, "", "   "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.make_attempt(training_mode="FOCUSED", focus_error_id=value)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_attempt(training_mode="PRACTICE")

    def test_required_text_fields_cannot_be_empty(self):
        for name in ("market_scenario", "observation_task", "primary_objective",
                     "target_concept_id", "user_analysis"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.make_attempt(**{name: "  "})

    def test_initial_analysis_and_context_cannot_be_overwritten(self):
        attempt = self.make_attempt()
        with self.assertRaises(FrozenInstanceError):
            attempt.user_analysis = "Rewritten after feedback"
        with self.assertRaises(FrozenInstanceError):
            attempt.context.market_scenario = "new scenario"
        with self.assertRaises(FrozenInstanceError):
            attempt.context.observation_task = "new task"
        with self.assertRaises(FrozenInstanceError):
            attempt.context.primary_objective = "new objective"
        with self.assertRaises(FrozenInstanceError):
            attempt.context.target_concept_id = S2
        with self.assertRaises(FrozenInstanceError):
            attempt.context.knowledge_boundary = None

    def test_context_has_exactly_one_primary_objective_and_target(self):
        attempt = self.make_attempt()
        self.assertEqual(
            {field.name for field in fields(type(attempt.context))},
            {"market_scenario", "observation_task", "primary_objective",
             "target_concept_id", "training_mode", "focus_error_id", "knowledge_boundary"},
        )
        self.assertEqual(attempt.context.primary_objective,
                         "Describe the high before interpreting it")
        self.assertEqual(attempt.context.target_concept_id, S1)

    def test_all_supported_stages_accept_their_own_concepts(self):
        for stage, concept in (("S1", S1), ("S2", S2), ("S3", S3)):
            with self.subTest(stage=stage):
                attempt = self.make_attempt(stage=stage, target_concept_id=concept,
                                            learned_concept_ids={concept})
                self.assertEqual(attempt.stage, stage)
                self.assertEqual(attempt.context.knowledge_boundary.stage, stage)

    def test_s4_and_unknown_stages_are_rejected(self):
        for stage in ("S4", "S8", "UNKNOWN", ""):
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                self.make_attempt(stage=stage)

    def test_s1_rejects_future_learned_concepts(self):
        for concept in (S2, S3):
            with self.subTest(concept=concept), self.assertRaises(ValueError):
                self.make_attempt(learned_concept_ids={S1, concept})

    def test_s2_rejects_s3_learned_concept(self):
        with self.assertRaises(ValueError):
            self.make_attempt(stage="S2", target_concept_id=S2,
                              learned_concept_ids={S1, S3})

    def test_unknown_learned_concept_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_attempt(learned_concept_ids={"CON-S1-INVENTED"})

    def test_canonical_cumulative_boundaries_have_exact_counts(self):
        s1 = {
            "CON-S1-HIGH", "CON-S1-LOW", "CON-S1-SWING-HIGH", "CON-S1-SWING-LOW",
            "CON-S1-HH", "CON-S1-HL", "CON-S1-LH", "CON-S1-LL",
            "CON-S1-UPTREND", "CON-S1-DOWNTREND", "CON-S1-RANGE",
            "CON-S1-UNCERTAIN", "CON-S1-FACT-VS-INTERPRETATION",
        }
        s2 = {
            "CON-S2-IMPULSE", "CON-S2-PULLBACK", "CON-S2-STRUCTURE-MAINTAINED",
            "CON-S2-STRUCTURE-WEAKENED", "CON-S2-STRUCTURE-DAMAGED",
            "CON-S2-STRUCTURE-CHANGED",
        }
        s3 = {
            "CON-S3-PREVIOUS-SIGNIFICANT-HIGH",
            "CON-S3-PREVIOUS-SIGNIFICANT-LOW", "CON-S3-MAJOR-SWING-HIGH",
            "CON-S3-MAJOR-SWING-LOW", "CON-S3-RANGE-HIGH", "CON-S3-RANGE-LOW",
            "CON-S3-STRUCTURAL-AREA", "CON-S3-CURRENT-LOCATION",
            "CON-S3-RELEVANT-VS-LESS-RELEVANT",
        }
        expected = {"S1": s1, "S2": s1 | s2, "S3": s1 | s2 | s3}
        for stage, target, count in (("S1", S1, 13), ("S2", S2, 19), ("S3", S3, 28)):
            with self.subTest(stage=stage):
                boundary = self.make_attempt(stage=stage, target_concept_id=target,
                                             learned_concept_ids=()).context.knowledge_boundary
                self.assertEqual(len(boundary.allowed_concept_ids), count)
                self.assertEqual(boundary.allowed_concept_ids, expected[stage])
                self.assertIn(target, boundary.allowed_concept_ids)
                self.assertEqual(len(boundary.concept_confidence), count)
                self.assertEqual(set(boundary.concept_confidence),
                                 {(concept, "CORE") for concept in boundary.allowed_concept_ids})

    def test_allowed_boundary_cannot_be_supplied_or_forged(self):
        with self.assertRaises(TypeError):
            self.make_attempt(allowed_concept_ids={"CON-S1-INVENTED"})
        actual = self.make_attempt().context.knowledge_boundary
        with self.assertRaises(ValueError):
            KnowledgeBoundary(stage="S1", allowed_concept_ids={S1, S2},
                              learned_concept_ids={S1}, concept_confidence=((S1, "CORE"),),
                              learning_map_reference=actual.learning_map_reference)

    def test_target_is_required(self):
        for target in (None, "", "  "):
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.make_attempt(target_concept_id=target)

    def test_s1_rejects_future_targets(self):
        for concept in (S2, S3):
            with self.subTest(concept=concept), self.assertRaises(ValueError):
                self.make_attempt(target_concept_id=concept)

    def test_s2_rejects_s3_target(self):
        with self.assertRaises(ValueError):
            self.make_attempt(stage="S2", target_concept_id=S3)

    def test_unknown_target_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_attempt(target_concept_id="CON-S1-INVENTED")

    def test_allowed_target_need_not_yet_be_learned(self):
        attempt = self.make_attempt(learned_concept_ids=())
        self.assertEqual(attempt.context.target_concept_id, S1)
        self.assertEqual(attempt.context.knowledge_boundary.learned_concept_ids, frozenset())

    def test_caller_source_mutation_does_not_change_saved_boundary(self):
        learned = [S1]
        attempt = self.make_attempt(learned_concept_ids=learned)
        learned.append(S2)
        self.assertEqual(attempt.context.knowledge_boundary.learned_concept_ids,
                         frozenset({S1}))
        self.assertEqual(attempt.context.target_concept_id, S1)
        self.assertEqual(attempt.context.market_scenario,
                         "An observable sequence of swing highs and lows")
        self.assertEqual(attempt.context.observation_task, "Identify the observed high")
        self.assertEqual(attempt.context.primary_objective,
                         "Describe the high before interpreting it")
        self.assertEqual(attempt.user_analysis, "The chosen interval has a visible high.")

    def test_later_learning_does_not_rewrite_submission_history(self):
        learned = {S1}
        attempt = self.make_attempt(learned_concept_ids=learned)
        learned.add(S2)
        self.assertEqual(attempt.context.knowledge_boundary.learned_concept_ids,
                         frozenset({S1}))
        self.assertEqual(attempt.context.knowledge_boundary.stage, "S1")
        self.assertEqual(len(attempt.context.knowledge_boundary.allowed_concept_ids), 13)

    def test_learning_map_reference_is_exact_and_immutable(self):
        reference = self.make_attempt().context.knowledge_boundary.learning_map_reference
        self.assertIs(type(reference), LearningMapReference)
        self.assertEqual(reference.commit, "65cd6969e8ccf890d6e51b07fd7436564bf70421")
        self.assertEqual(reference.path, "spec/learning_map/LEARNING_MAP_SPEC.md")
        self.assertEqual(reference.blob, "726b35db8409ea03cbec33c916db7374e6724e03")
        with self.assertRaises(FrozenInstanceError):
            reference.commit = "another commit"

    def test_training_returns_only_attempt_without_evaluation_behavior(self):
        attempt = self.make_attempt()
        self.assertIs(type(attempt), TrainingAttempt)
        self.assertEqual(attempt.user_analysis, "The chosen interval has a visible high.")
        self.assertFalse(hasattr(attempt, "evaluation"))
        self.assertFalse(hasattr(attempt, "learning_state"))


if __name__ == "__main__":
    unittest.main()
