import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from practice_checkpoint import CheckpointError, PracticeCheckpoint
import test_question_batches as fixtures


class ResumeTests(unittest.TestCase):
    response = fixtures.QuestionBatchTests.response

    def setUp(self):
        fixtures.QuestionBatchTests.setUp(self)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.identity = {'title': 'Resume test', 'grade': 4}
        self.context = {'rules': 'original rules'}

    def open_checkpoint(self):
        return PracticeCheckpoint(self.directory.name, self.identity)

    def generate(self, checkpoint):
        with patch.object(self.m, 'request_practice_set', side_effect=self.response):
            return self.m.generate_planned_practice_set(
                'Rules', 'Test', self.plan, self.sections, self.topics, 2,
                checkpoint=checkpoint,
            )

    def test_restart_after_mid_review_failure_reuses_completed_questions(self):
        review_calls = []
        interrupted = False
        def review_response(system, user, *args):
            nonlocal interrupted
            batch = json.loads(user)['questions']
            positions = [q['position'] for q in batch]
            review_calls.append(positions)
            if positions == [5, 7] and not interrupted:
                interrupted = True
                raise KeyboardInterrupt('script stopped')
            return {'questions': [dict(position=q['position'],
                topic_id=self.questions[q['position']].topic_id, correct_answer='4',
                unambiguous=True, detailed_solution_latex='Verified solution.') for q in batch]}

        with patch.object(self.m, 'review_practice_set', self.real_review), patch.object(
                self.m, 'request_structured_json', side_effect=review_response):
            with self.open_checkpoint() as checkpoint:
                checkpoint.load(self.context)
                checkpoint.initialize(self.plan)
                with self.assertRaises(KeyboardInterrupt):
                    self.generate(checkpoint)
                saved = json.loads(checkpoint.path.read_text())
                self.assertEqual([p for p, row in saved['questions'].items()
                                  if row['status'] == 'completed'], ['1', '3', '4'])
                self.assertEqual(saved['questions']['5']['status'], 'draft')
            self.calls.clear()
            with self.open_checkpoint() as restarted:
                saved = restarted.load(self.context)
                self.plan = self.m.WholeSetPlan.model_validate(saved['plan'])
                result = self.generate(restarted)
            self.assertEqual(self.calls, [[5, 7], [2, 6]])
            self.assertEqual([q.position for q in result.questions], list(range(1, 8)))
            self.assertEqual(review_calls.count([1, 3, 4]), 1)

    def test_completed_checkpoint_makes_no_generation_or_review_calls(self):
        with self.open_checkpoint() as checkpoint:
            checkpoint.load(self.context)
            checkpoint.initialize(self.plan)
            original = self.generate(checkpoint)
        self.calls.clear()
        self.review.reset_mock()
        with self.open_checkpoint() as checkpoint:
            checkpoint.load(self.context)
            resumed = self.generate(checkpoint)
        self.assertEqual(resumed.model_dump(), original.model_dump())
        self.assertEqual(self.calls, [])
        self.review.assert_not_called()

    def test_changed_context_and_corrupt_json_fail_without_overwriting(self):
        with self.open_checkpoint() as checkpoint:
            checkpoint.load(self.context)
            checkpoint.initialize(self.plan)
            original = checkpoint.path.read_bytes()
            with self.assertRaises(CheckpointError):
                checkpoint.load({'rules': 'changed'})
            self.assertEqual(checkpoint.path.read_bytes(), original)
            checkpoint.path.write_text('{broken')
            with self.assertRaises(CheckpointError):
                checkpoint.load(self.context)
            self.assertEqual(checkpoint.path.read_text(), '{broken')

    def test_invalid_completed_question_is_not_trusted(self):
        with self.open_checkpoint() as checkpoint:
            checkpoint.load(self.context)
            checkpoint.initialize(self.plan)
            self.generate(checkpoint)
            checkpoint.data['questions']['1']['question']['correct_answer'] = 'not an integer'
            checkpoint.save()
        self.calls.clear()
        with self.open_checkpoint() as checkpoint:
            checkpoint.load(self.context)
            with self.assertRaises(CheckpointError):
                self.generate(checkpoint)
        self.assertEqual(self.calls, [])

    def test_failed_atomic_replace_preserves_previous_checkpoint(self):
        with self.open_checkpoint() as checkpoint:
            checkpoint.load(self.context)
            checkpoint.initialize(self.plan)
            original = checkpoint.path.read_bytes()
            with patch('practice_checkpoint.os.replace', side_effect=OSError('disk failure')):
                with self.assertRaises(CheckpointError):
                    checkpoint.complete(self.questions[1], 'duplicate text')
            self.assertEqual(checkpoint.path.read_bytes(), original)
            self.assertEqual(len(list(Path(self.directory.name).glob('*.json.*'))), 0)

    def test_exclusive_lock_is_released_after_interruption(self):
        with self.assertRaises(KeyboardInterrupt):
            with self.open_checkpoint():
                with self.assertRaisesRegex(CheckpointError, 'Another generator'):
                    with self.open_checkpoint():
                        pass
                raise KeyboardInterrupt()
        with self.open_checkpoint():
            pass


if __name__ == '__main__':
    unittest.main()
