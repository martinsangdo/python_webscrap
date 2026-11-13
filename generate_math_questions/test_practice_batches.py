import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch


class PracticeBatchTests(unittest.TestCase):
    def setUp(self):
        with patch('supabase.create_client'):
            self.module = importlib.import_module('ai_questions')
        self.db = MagicMock()
        query = self.db.table.return_value
        for method in ('select', 'eq', 'order'):
            getattr(query, method).return_value = query
        self.levels = [
            {'level_code': 'JUNIOR', 'target_grade_min': 3, 'target_grade_max': 4},
            {'level_code': 'SENIOR', 'target_grade_min': 4, 'target_grade_max': 5},
        ]
        query.execute.return_value = SimpleNamespace(data=self.levels)
        db_patch = patch.object(self.module, 'supabase', self.db)
        single_patch = patch.object(self.module, '_generate_single_practice_set')
        db_patch.start()
        self.single = single_patch.start()
        self.addCleanup(db_patch.stop)
        self.addCleanup(single_patch.stop)

    def test_all_level_grade_combinations(self):
        self.module.generate_complete_practice_set(certification_id='TEST', set_title='Model')
        self.single.assert_has_calls([
            call('TEST', code, f'Model - {code} - Grade {grade}', grade, 3)
            for code, grade in [('JUNIOR', 3), ('JUNIOR', 4), ('SENIOR', 4), ('SENIOR', 5)]
        ])
        self.assertEqual(self.single.call_count, 4)
        self.db.table.return_value.eq.assert_called_once_with('certification_id', 'TEST')

    def test_grade_filters_levels(self):
        self.module.generate_complete_practice_set('TEST', set_title='Model', grade=3, max_attempts=2)
        self.single.assert_called_once_with('TEST', 'JUNIOR', 'Model - JUNIOR - Grade 3', 3, 2)

    def test_existing_positional_call_preserved(self):
        self.module.generate_complete_practice_set('TEST', 'JUNIOR', 'Model')
        self.single.assert_called_once_with('TEST', 'JUNIOR', 'Model', None, 3)
        self.db.table.assert_not_called()

    def test_no_matching_grades(self):
        with self.assertRaisesRegex(ValueError, 'No matching'):
            self.module.generate_complete_practice_set('TEST', set_title='Model', grade=10)
        self.single.assert_not_called()

    def test_empty_levels(self):
        self.levels.clear()
        with self.assertRaisesRegex(ValueError, 'No matching'):
            self.module.generate_complete_practice_set('TEST', set_title='Model')
        self.single.assert_not_called()

    def test_invalid_inputs_do_not_generate(self):
        for kwargs in ({}, {'set_title': ' '}, {'set_title': 'Model', 'grade': True},
                       {'set_title': 'Model', 'max_attempts': 0}, {'set_title': 'x' * 128}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.module.generate_complete_practice_set('TEST', **kwargs)
        self.single.assert_not_called()

    def test_prevalidates_all_ranges(self):
        self.levels[-1]['target_grade_max'] = None
        with self.assertRaisesRegex(ValueError, 'Invalid grade range'):
            self.module.generate_complete_practice_set('TEST', set_title='Model')
        self.single.assert_not_called()

    def test_stops_after_failure(self):
        self.single.side_effect = [None, RuntimeError('generation failed')]
        with self.assertRaisesRegex(RuntimeError, 'generation failed'):
            self.module.generate_complete_practice_set('TEST', set_title='Model')
        self.assertEqual(self.single.call_count, 2)

    def test_existing_sets_are_skipped_and_remaining_combinations_generated(self):
        self.single.side_effect = [
            self.module.PracticeSetAlreadyExistsError('JUNIOR grade 3'),
            None,
            self.module.PracticeSetAlreadyExistsError('SENIOR grade 4'),
            None,
        ]
        with patch('builtins.print') as output:
            self.module.generate_complete_practice_set('TEST', set_title='Model')
        self.assertEqual(self.single.call_count, 4)
        self.assertEqual(self.single.call_args.args, ('TEST', 'SENIOR', 'Model - SENIOR - Grade 5', 5, 3))
        output.assert_any_call('=== Batch complete: 2 created, 2 skipped ===')

    def test_all_existing_sets_complete_without_error(self):
        self.single.side_effect = self.module.PracticeSetAlreadyExistsError('Already saved')
        with patch('builtins.print') as output:
            self.module.generate_complete_practice_set('TEST', set_title='Model')
        self.assertEqual(self.single.call_count, 4)
        output.assert_any_call('=== Batch complete: 0 created, 4 skipped ===')

    def test_explicit_level_still_reports_duplicate(self):
        self.single.side_effect = self.module.PracticeSetAlreadyExistsError('Already saved')
        with self.assertRaises(self.module.PracticeSetAlreadyExistsError):
            self.module.generate_complete_practice_set('TEST', 'JUNIOR', 'Model')

    def test_validation_errors_are_not_mistaken_for_duplicates(self):
        self.single.side_effect = ValueError('Invalid question')
        with self.assertRaisesRegex(ValueError, 'Invalid question'):
            self.module.generate_complete_practice_set('TEST', set_title='Model')
        self.single.assert_called_once()
