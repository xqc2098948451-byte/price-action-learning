"""Review behavior and ordinary construction/restoration contract attacks."""

import copy
import copyreg
import importlib
import importlib.util
import inspect
import itertools
import pickle
import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone, tzinfo
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from price_action_learning.evaluation import create_evaluation
from price_action_learning.learning_state import create_learning_state, apply_evaluation
from price_action_learning.training import create_training_attempt


START = datetime(2026, 1, 1, tzinfo=timezone.utc)
RECORD_FIELDS = ('id', 'source_attempt_id', 'error_id', 'scheduled_for',
                 'completed_at', 'new_analysis', 'result')


class SpoofText(str):
    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash('OBS-001')


class DateSubclass(datetime):
    pass


class OtherUTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)

    def dst(self, dt):
        return timedelta(0)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('price_action_learning.review'),
                             'the approved Review API must exist')
        self.api = importlib.import_module('price_action_learning.review')

    def attempt(self, *, at=START, stage='S1', learned=None, mode='FORMAL',
                focus=None, analysis='A fresh synthetic interval analysis.'):
        class Clock:
            @staticmethod
            def now(zone):
                return at
        values = dict(stage=stage, market_scenario='Synthetic visible interval',
                      observation_task='Describe visible structure',
                      primary_objective='Separate fact and interpretation',
                      target_concept_id='CON-S1-HIGH', training_mode=mode,
                      focus_error_id=focus, learned_concept_ids=(), user_analysis=analysis)
        with patch('price_action_learning.training.core.datetime', Clock):
            if learned is None:
                learned = create_training_attempt(**values).context.knowledge_boundary.allowed_concept_ids
            values['learned_concept_ids'] = learned
            return create_training_attempt(**values)

    def evaluation(self, attempt, **signals):
        values = dict(attempt=attempt, evaluation_confidence='HIGH', abstain=False)
        values.update(signals)
        return create_evaluation(**values)

    def bundle(self, *, stage='S1', learned=None, **signals):
        source = self.attempt(stage=stage, learned=learned, analysis='Old answer stays hidden.')
        values = dict(primary_error='OBS-001')
        values.update(signals)
        evaluation = self.evaluation(source, **values)
        state = apply_evaluation(state=create_learning_state(current_stage=stage),
                                 attempt=source, evaluation=evaluation)
        records = self.api.schedule_reviews(state=state, source_attempt=source, evaluation=evaluation)
        return state, source, evaluation, records

    def arguments(self, record, source, *, prior=(), signals=None, **fresh):
        values = dict(at=record.scheduled_for, stage=source.stage, mode='FOCUSED',
                      focus=record.error_id)
        values.update(fresh)
        attempt = self.attempt(**values)
        evaluation = self.evaluation(attempt, **(signals or {}))
        return dict(record=record, source_attempt=source, review_attempt=attempt,
                    review_evaluation=evaluation, completed_at=record.scheduled_for,
                    prior_reviews=prior)

    def complete(self, record, source, *, prior=(), signals=None, **fresh):
        return self.api.complete_review(**self.arguments(record, source, prior=prior,
                                                        signals=signals, **fresh))

    def pair(self, records, source, results=('IMPROVING', 'IMPROVING')):
        signal = {'IMPROVING': {}, 'REPEATED': {'primary_error': 'OBS-001'},
                  'INCONCLUSIVE': {'abstain': True}}
        return tuple(self.complete(record, source, signals=signal[result])
                     for record, result in zip(records[:2], results))

    def forge(self, record, **overrides):
        # Deliberately malformed fixtures, not a supported provenance mechanism.
        result = object.__new__(type(record))
        for field in fields(record):
            object.__setattr__(result, field.name, overrides.get(field.name, getattr(record, field.name)))
        return result

    def snapshot(self, record):
        return tuple(getattr(record, field.name) for field in fields(record))

    def bad_schedule(self, **overrides):
        state, source, evaluation, _ = self.bundle()
        args = dict(state=state, source_attempt=source, evaluation=evaluation)
        args.update(overrides)
        with self.assertRaises(ValueError):
            self.api.schedule_reviews(**args)

    def bad_complete(self, **overrides):
        _, source, _, records = self.bundle()
        args = self.arguments(records[2], source)
        args.update(overrides)
        with self.assertRaises(ValueError):
            self.api.complete_review(**args)

    def test_01_exact_fields_slots_and_exports(self):
        _, _, _, records = self.bundle()
        self.assertEqual(tuple(f.name for f in fields(records[0])), RECORD_FIELDS)
        self.assertEqual(records[0].__slots__, RECORD_FIELDS)
        self.assertFalse(hasattr(records[0], '__dict__'))
        self.assertEqual(self.api.__all__, ['ReviewRecord', 'schedule_reviews', 'complete_review'])

    def test_02_source_anchored_three_ordered_schedules(self):
        _, source, _, records = self.bundle()
        self.assertIs(type(records), tuple)
        self.assertEqual(len(records), 3)
        self.assertEqual(tuple(r.scheduled_for for r in records),
                         (START+timedelta(days=3), START+timedelta(days=7), START+timedelta(days=30)))
        for record in records:
            self.assertEqual(record.source_attempt_id, source.id)
            self.assertEqual(record.error_id, 'OBS-001')
            self.assertEqual((record.completed_at, record.new_analysis, record.result), (None, None, None))
            self.assertIs(type(record.scheduled_for), datetime)
            self.assertIs(record.scheduled_for.tzinfo, timezone.utc)

    def test_03_distinct_canonical_uuid4_ids(self):
        _, _, _, records = self.bundle()
        self.assertEqual(len({r.id for r in records}), 3)
        for record in records:
            self.assertIs(type(record.id), str)
            self.assertEqual(str(UUID(record.id)), record.id)
            self.assertEqual(UUID(record.id).version, 4)

    def test_04_focus_in_contributors_is_scheduled(self):
        state, source, _, _ = self.bundle()
        evaluation = self.evaluation(source, primary_error='OBS-002', contributors=('OBS-001',))
        records = self.api.schedule_reviews(state=state, source_attempt=source, evaluation=evaluation)
        self.assertEqual(tuple(r.error_id for r in records), ('OBS-001',)*3)

    def test_05_schedule_abstain_rejects(self):
        state, source, _, _ = self.bundle()
        with self.assertRaises(ValueError):
            self.api.schedule_reviews(state=state, source_attempt=source,
                                      evaluation=self.evaluation(source, abstain=True))

    def test_06_schedule_no_formal_error_rejects(self):
        state, source, _, _ = self.bundle()
        with self.assertRaises(ValueError):
            self.api.schedule_reviews(state=state, source_attempt=source, evaluation=self.evaluation(source))

    def test_07_schedule_missing_focus_rejects(self):
        self.bad_schedule(state=create_learning_state(current_stage='S1'))

    def test_08_schedule_focus_mismatch_rejects(self):
        state, source, _, _ = self.bundle()
        with self.assertRaises(ValueError):
            self.api.schedule_reviews(state=state, source_attempt=source,
                                      evaluation=self.evaluation(source, primary_error='OBS-002'))

    def test_09_schedule_evaluation_binding_rejects(self):
        self.bad_schedule(evaluation=self.evaluation(self.attempt(), primary_error='OBS-001'))

    def test_10_schedule_stage_binding_rejects(self):
        self.bad_schedule(state=create_learning_state(current_stage='S2'))

    def test_11_schedule_exact_record_types(self):
        state, source, evaluation, _ = self.bundle()
        for key, obj in (('state', state), ('source_attempt', source), ('evaluation', evaluation)):
            for value in (SimpleNamespace(**dict(zip((f.name for f in fields(obj)), self.snapshot(obj)))),
                          self.subclass_value(obj)):
                with self.subTest(key=key, type=type(value)):
                    self.bad_schedule(**{key: value})

    def subclass_value(self, record):
        subclass = type('DerivedRecord', (type(record),), {})
        result = object.__new__(subclass)
        for field in fields(record):
            object.__setattr__(result, field.name, getattr(record, field.name))
        return result

    def test_12_day3_absence_improves(self):
        _, source, _, records = self.bundle()
        self.assertEqual(self.complete(records[0], source).result, 'IMPROVING')

    def test_13_day7_absence_improves(self):
        _, source, _, records = self.bundle()
        self.assertEqual(self.complete(records[1], source).result, 'IMPROVING')

    def test_14_primary_recurrence_repeats(self):
        _, source, _, records = self.bundle()
        for record in records:
            self.assertEqual(self.complete(record, source, signals={'primary_error': 'OBS-001'}).result, 'REPEATED')

    def test_15_contributor_recurrence_repeats(self):
        _, source, _, records = self.bundle()
        self.assertEqual(self.complete(records[2], source,
                         signals={'primary_error': 'OBS-002', 'contributors': ('OBS-001',)}).result, 'REPEATED')

    def test_16_abstention_is_inconclusive(self):
        _, source, _, records = self.bundle()
        for record in records:
            self.assertEqual(self.complete(record, source, signals={'abstain': True}).result, 'INCONCLUSIVE')

    def test_17_day30_empty_tuple_is_valid_incomplete_evidence(self):
        _, source, _, records = self.bundle()
        self.assertEqual(self.complete(records[2], source, prior=()).result, 'IMPROVING')

    def test_18_pre001_only_valid_day3_improves(self):
        _, source, _, records = self.bundle()
        day3 = self.complete(records[0], source)
        self.assertEqual(self.complete(records[2], source, prior=(day3,)).result, 'IMPROVING')

    def test_19_pre001_only_valid_day7_improves(self):
        _, source, _, records = self.bundle()
        day7 = self.complete(records[1], source)
        self.assertEqual(self.complete(records[2], source, prior=(day7,)).result, 'IMPROVING')

    def test_20_complete_improving_chain_resolves(self):
        _, source, _, records = self.bundle()
        self.assertEqual(self.complete(records[2], source, prior=self.pair(records, source)).result, 'RESOLVED')

    def test_21_repeated_chain_is_valid_improving(self):
        _, source, _, records = self.bundle()
        for outcomes in (('REPEATED', 'IMPROVING'), ('IMPROVING', 'REPEATED'), ('REPEATED', 'REPEATED')):
            self.assertEqual(self.complete(records[2], source, prior=self.pair(records, source, outcomes)).result, 'IMPROVING')

    def test_22_inconclusive_chain_is_valid_improving(self):
        _, source, _, records = self.bundle()
        for outcomes in (('INCONCLUSIVE', 'IMPROVING'), ('IMPROVING', 'INCONCLUSIVE'), ('INCONCLUSIVE', 'INCONCLUSIVE')):
            self.assertEqual(self.complete(records[2], source, prior=self.pair(records, source, outcomes)).result, 'IMPROVING')

    def test_23_all_ordered_predecessor_result_pairs(self):
        _, source, _, records = self.bundle()
        for outcomes in itertools.product(('IMPROVING', 'REPEATED', 'INCONCLUSIVE'), repeat=2):
            expected = 'RESOLVED' if outcomes == ('IMPROVING', 'IMPROVING') else 'IMPROVING'
            self.assertEqual(self.complete(records[2], source, prior=self.pair(records, source, outcomes)).result, expected)

    def test_24_wrong_predecessor_source_rejects(self):
        self.assert_bad_predecessor(source_attempt_id=str(uuid4()))

    def test_25_wrong_predecessor_error_rejects(self):
        self.assert_bad_predecessor(error_id='OBS-002')

    def test_26_wrong_predecessor_slot_rejects(self):
        self.assert_bad_predecessor(scheduled_for=START+timedelta(days=4), completed_at=START+timedelta(days=4))

    def assert_bad_predecessor(self, **overrides):
        _, source, _, records = self.bundle()
        predecessor = self.forge(self.complete(records[0], source), **overrides)
        with self.assertRaises(ValueError):
            self.complete(records[2], source, prior=(predecessor,))

    def test_27_duplicate_predecessor_id_rejects(self):
        _, source, _, records = self.bundle()
        day3, day7 = self.pair(records, source)
        with self.assertRaises(ValueError):
            self.complete(records[2], source, prior=(day3, self.forge(day7, id=day3.id)))

    def test_28_duplicate_slot_rejects(self):
        _, source, _, records = self.bundle()
        day3 = self.complete(records[0], source)
        with self.assertRaises(ValueError):
            self.complete(records[2], source, prior=(day3, self.forge(day3, id=str(uuid4()))))

    def test_29_wrong_pair_order_rejects(self):
        _, source, _, records = self.bundle()
        with self.assertRaises(ValueError):
            self.complete(records[2], source, prior=self.pair(records, source)[::-1])

    def test_30_extra_predecessor_rejects(self):
        _, source, _, records = self.bundle()
        pair = self.pair(records, source)
        with self.assertRaises(ValueError):
            self.complete(records[2], source, prior=pair+(pair[0],))

    def test_31_uncompleted_predecessor_rejects(self):
        _, source, _, records = self.bundle()
        with self.assertRaises(ValueError):
            self.complete(records[2], source, prior=(records[0],))

    def test_32_predecessor_after_current_completion_rejects(self):
        self.assert_bad_predecessor(completed_at=START+timedelta(days=31))

    def test_33_resolution_tuple_and_members_exact(self):
        _, source, _, records = self.bundle()
        day3 = self.complete(records[0], source)
        class TupleSubclass(tuple):
            pass
        for prior in (None, [], [day3], TupleSubclass((day3,)), (None,), (object(),),
                      (self.subclass_value(day3),), (SimpleNamespace(**dict(zip(RECORD_FIELDS,self.snapshot(day3)))),)):
            with self.subTest(prior=type(prior)), self.assertRaises(ValueError):
                self.complete(records[2], source, prior=prior)

    def test_34_predecessor_does_not_gate_abstention(self):
        _, source, _, records = self.bundle()
        for prior in (None, [object()], (object(),)*3):
            self.assertEqual(self.complete(records[2], source, prior=prior, signals={'abstain': True}).result, 'INCONCLUSIVE')

    def test_35_predecessor_does_not_gate_recurrence(self):
        _, source, _, records = self.bundle()
        for prior in (None, [object()], (object(),)*3):
            self.assertEqual(self.complete(records[2], source, prior=prior,
                                          signals={'primary_error': 'OBS-001'}).result, 'REPEATED')

    def test_36_day3_day7_require_no_predecessor_chain(self):
        _, source, _, records = self.bundle()
        for record in records[:2]:
            self.assertEqual(self.complete(record, source, prior=(object(),)).result, 'IMPROVING')

    def test_37_fresh_attempt_id_required(self):
        _, source, _, records = self.bundle()
        args = self.arguments(records[2], source)
        fresh = self.forge(args['review_attempt'], id=source.id)
        args.update(review_attempt=fresh, review_evaluation=self.forge(args['review_evaluation'], attempt_id=source.id))
        with self.assertRaises(ValueError):
            self.api.complete_review(**args)

    def test_38_focused_mode_required(self):
        _, source, _, records = self.bundle()
        with self.assertRaises(ValueError):
            self.complete(records[0], source, mode='FORMAL', focus=None)

    def test_39_review_focus_binding_required(self):
        _, source, _, records = self.bundle()
        with self.assertRaises(ValueError):
            self.complete(records[0], source, focus='OBS-002')

    def test_40_review_stage_binding_required(self):
        _, source, _, records = self.bundle()
        with self.assertRaises(ValueError):
            self.complete(records[0], source, stage='S2')

    def test_41_knowledge_regression_rejects(self):
        _, source, _, records = self.bundle()
        with self.assertRaises(ValueError):
            self.complete(records[0], source, learned=())

    def test_42_knowledge_expansion_allowed(self):
        _, source, _, records = self.bundle(learned=('CON-S1-HIGH',))
        self.assertEqual(self.complete(records[0], source).result, 'IMPROVING')

    def test_43_fresh_evaluation_binding_required(self):
        self.bad_complete(review_evaluation=self.evaluation(self.attempt()))

    def test_44_early_completion_rejects(self):
        self.bad_complete(completed_at=START+timedelta(days=29))

    def test_45_exact_datetime_and_utc_identity(self):
        for time in (None, '2026-02-01', START.replace(tzinfo=None),
                     START.replace(tzinfo=timezone(timedelta(hours=8))),
                     START.replace(tzinfo=OtherUTC()), DateSubclass(2026,2,1,tzinfo=timezone.utc)):
            with self.subTest(type=type(time)):
                self.bad_complete(completed_at=time)

    def test_46_new_analysis_from_fresh_attempt_only(self):
        _, source, _, records = self.bundle()
        result = self.complete(records[0], source, analysis='Independent new analysis.')
        self.assertEqual(result.new_analysis, 'Independent new analysis.')
        self.assertIs(type(result.new_analysis), str)

    def test_47_source_answer_does_not_determine_result(self):
        _, source, _, records = self.bundle()
        for answer in ('Changed old answer.', 'OBS-001 old answer.', object()):
            changed = self.forge(source, user_analysis=answer)
            self.assertEqual(self.complete(records[0], changed).result, 'IMPROVING')

    def test_48_no_old_evaluation_or_market_arguments(self):
        _, source, evaluation, records = self.bundle()
        args = self.arguments(records[0], source)
        for key in ('source_evaluation', 'old_analysis', 'old_evaluation', 'GPT_feedback',
                    'future_candles', 'future_price', 'market_result', 'realized_pnl', 'trade_result'):
            with self.subTest(key=key), self.assertRaises(TypeError):
                self.api.complete_review(**args, **{key:evaluation})
        self.assertEqual(tuple(inspect.signature(self.api.complete_review).parameters),
                         ('record','source_attempt','review_attempt','review_evaluation','completed_at','prior_reviews'))
        self.assertEqual(tuple(inspect.signature(self.api.schedule_reviews).parameters),
                         ('state','source_attempt','evaluation'))

    def test_49_diagnostic_prose_does_not_determine_result(self):
        _, source, _, records = self.bundle()
        for prose in ('This looks repeated.', 'This looks resolved.'):
            self.assertEqual(self.complete(records[0], source,
                             signals={'primary_issue':prose,'hint':prose,'what_was_correct':(prose,)}).result, 'IMPROVING')

    def test_50_predecessor_analysis_does_not_determine_result(self):
        _, source, _, records = self.bundle()
        pair = self.pair(records, source)
        changed = tuple(self.forge(r,new_analysis='Unrelated prior analysis.') for r in pair)
        self.assertEqual(self.complete(records[2], source, prior=changed).result, 'RESOLVED')

    def test_51_new_record_preserves_four_fields_and_all_inputs(self):
        state, source, evaluation, records = self.bundle()
        args = self.arguments(records[0], source)
        inputs = (state,source,evaluation,records[0],args['review_attempt'],args['review_evaluation'])
        before = [self.snapshot(r) for r in inputs]
        result = self.api.complete_review(**args)
        self.assertIsNot(result, records[0])
        self.assertEqual(self.snapshot(result)[:4], self.snapshot(records[0])[:4])
        self.assertEqual(before, [self.snapshot(r) for r in inputs])
        self.assertEqual(state.reviews_due, ())

    def test_52_direct_and_copied_construction_blocked(self):
        _, _, _, records = self.bundle()
        with self.assertRaises(TypeError):
            self.api.ReviewRecord()
        with self.assertRaises(TypeError):
            self.api.ReviewRecord(**dict(zip(RECORD_FIELDS,self.snapshot(records[0]))))

    def test_53_replace_copy_and_deepcopy_blocked(self):
        _, source, _, records = self.bundle()
        for record in (records[0], self.complete(records[0],source)):
            before = self.snapshot(record)
            for operation in (replace,copy.copy,copy.deepcopy):
                with self.assertRaises(TypeError):
                    operation(record)
            self.assertEqual(self.snapshot(record), before)

    def test_54_pickle_all_protocols_blocked(self):
        _, source, _, records = self.bundle()
        for record in (records[0],self.complete(records[0],source)):
            before = self.snapshot(record)
            for protocol in range(pickle.HIGHEST_PROTOCOL+1):
                with self.subTest(protocol=protocol),self.assertRaises(TypeError):
                    pickle.dumps(record,protocol=protocol)
                with self.assertRaises(TypeError):
                    record.__reduce_ex__(protocol)
            with self.assertRaises(TypeError):
                record.__reduce__()
            self.assertEqual(self.snapshot(record), before)

    def test_55_restoration_blocked_without_mutating_originals(self):
        _, source, _, records = self.bundle()
        for record in (records[0],self.complete(records[0],source)):
            before = self.snapshot(record)
            with self.assertRaises(TypeError):
                record.__setstate__(list(before))
            with self.assertRaises(TypeError):
                copyreg.__newobj__(self.api.ReviewRecord)
            with self.assertRaises(TypeError):
                copyreg.__newobj_ex__(self.api.ReviewRecord,(),{})
            self.assertEqual(self.snapshot(record), before)

    def test_56_record_immutable(self):
        _, source, _, records = self.bundle()
        for record in (records[0],self.complete(records[0],source)):
            with self.assertRaises((FrozenInstanceError,TypeError,AttributeError)):
                record.result='RESOLVED'
            with self.assertRaises((FrozenInstanceError,TypeError,AttributeError)):
                del record.error_id

    def test_57_partial_completion_combinations_reject(self):
        _, source, _, records = self.bundle()
        completed=dict(completed_at=records[0].scheduled_for,new_analysis='Fresh.',result='IMPROVING')
        for size in (1,2):
            for selected in itertools.combinations(completed,size):
                malformed=self.forge(records[0],**{key:completed[key] for key in selected})
                with self.assertRaises(ValueError):
                    self.complete(malformed,source)

    def test_58_completed_record_cannot_be_completed_again(self):
        _, source, _, records = self.bundle()
        with self.assertRaises(ValueError):
            self.complete(self.complete(records[0],source),source)

    def test_59_current_source_id_binding_required(self):
        _, source, _, records = self.bundle()
        with self.assertRaises(ValueError):
            self.complete(records[0],self.attempt())

    def test_60_current_slot_must_be_source_anchored(self):
        _, source, _, records = self.bundle()
        for offset in (2,4,6,8,29,31):
            malformed=self.forge(records[0],scheduled_for=START+timedelta(days=offset))
            with self.assertRaises(ValueError):
                self.complete(malformed,source)

    def test_61_completion_exact_types(self):
        _, source, _, records = self.bundle()
        args=self.arguments(records[0],source)
        for key in ('record','source_attempt','review_attempt','review_evaluation'):
            for value in (SimpleNamespace(),self.subclass_value(args[key])):
                changed=dict(args,**{key:value})
                with self.subTest(key=key),self.assertRaises(ValueError):
                    self.api.complete_review(**changed)

    def test_62_uuid_error_and_result_representations_reject(self):
        _, source, _, records = self.bundle()
        for changes in ({'id':'not-a-uuid'}, {'id':records[0].id.upper()},
                        {'source_attempt_id':SpoofText(source.id)}, {'error_id':SpoofText('OBS-001')},
                        {'error_id':'OBS-999'}, {'scheduled_for':START.replace(tzinfo=None)}):
            with self.assertRaises(ValueError):
                self.complete(self.forge(records[0],**changes),source)
        for result in ('RESOLVED ',SpoofText('IMPROVING'),object()):
            self.assert_bad_predecessor(result=result)

    def test_63_evaluation_spoofed_formal_values_reject(self):
        _, source, _, records = self.bundle()
        args=self.arguments(records[0],source)
        for changes in ({'attempt_id':SpoofText(args['review_attempt'].id)},
                        {'abstain':1}, {'primary_error':SpoofText('OBS-001')},
                        {'contributors':['OBS-001']}, {'contributors':('OBS-001','OBS-001')},
                        {'evaluation_confidence':'LOW'}):
            with self.assertRaises(ValueError):
                self.api.complete_review(**dict(args,review_evaluation=self.forge(args['review_evaluation'],**changes)))

    def test_64_current_record_id_cannot_be_predecessor_id(self):
        _, source, _, records = self.bundle()
        day3=self.forge(self.complete(records[0],source),id=records[2].id)
        with self.assertRaises(ValueError):
            self.complete(records[2],source,prior=(day3,))

    def test_65_no_learning_state_private_builder_access(self):
        # A patched forbidden operation fails immediately if Review calls it.
        state,source,evaluation,records=self.bundle()
        with patch('price_action_learning.learning_state.core._build_state',side_effect=AssertionError('forbidden')):
            self.api.schedule_reviews(state=state,source_attempt=source,evaluation=evaluation)
            self.assertEqual(self.complete(records[0],source).result,'IMPROVING')

    def test_66_all_stages_remain_at_their_source_stage(self):
        for stage in ('S1','S2','S3'):
            state,source,_,records=self.bundle(stage=stage)
            self.assertEqual(self.complete(records[0],source).result,'IMPROVING')
            self.assertEqual(state.current_stage,stage)

    def test_67_source_knowledge_elements_cannot_spoof_set_equality(self):
        class SpoofConcept(str):
            def __eq__(self, other):
                return True

            def __hash__(self):
                return hash('CON-S1-HIGH')
        _,source,_,records=self.bundle()
        boundary=self.forge(source.context.knowledge_boundary,
                            learned_concept_ids=frozenset((SpoofConcept('CON-S1-HIGH'),)))
        context=self.forge(source.context,knowledge_boundary=boundary)
        source=self.forge(source,context=context)
        with self.assertRaises(ValueError):
            self.complete(records[0],source)


if __name__ == '__main__':
    unittest.main()
