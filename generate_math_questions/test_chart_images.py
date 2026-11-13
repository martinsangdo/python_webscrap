import importlib
import json
import unittest
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from chart_images import diagram_folder, render_chart_svg


class ChartTests(unittest.TestCase):
    def test_render_types(self):
        for kind in ('BAR', 'LINE', 'PIE'):
            with self.subTest(kind=kind):
                svg = render_chart_svg(kind, {'categories': ['A', 'B'], 'values': [2, 3]})
                root = ET.fromstring(svg)
                self.assertTrue(root.tag.endswith('svg'))
                self.assertIn('viewBox', root.attrib)
                self.assertFalse(any(n.tag.endswith('image') for n in root.iter()))

    def test_geometry(self):
        svg = render_chart_svg('GEOMETRY_SVG', {'svg': '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="20"/></svg>'})
        self.assertEqual(ET.fromstring(svg).tag, '{http://www.w3.org/2000/svg}svg')
        for content in ('<script/>', '<image href="https://example.com/a.png"/>', '<path onclick="x()"/>'):
            with self.assertRaises(ValueError):
                render_chart_svg('GEOMETRY_SVG', {'svg': f'<svg viewBox="0 0 10 10">{content}</svg>'})

    def test_invalid_data(self):
        for data in ({'categories': ['A'], 'values': []}, {'categories': ['A'], 'values': [float('nan')]}, {'categories': ['A'], 'values': [True]}):
            with self.assertRaises(ValueError):
                render_chart_svg('BAR', data)
        with self.assertRaises(ValueError):
            render_chart_svg('PIE', {'categories': ['A'], 'values': [0]})

    def test_folders(self):
        level = {'target_grade_min': 4, 'target_grade_max': 4}
        self.assertEqual(diagram_folder('SASMO', 'PRIMARY_4', level, 3), 'SASMO/grade_4/PRIMARY_4/3')
        level['target_grade_max'] = 5
        self.assertEqual(diagram_folder('SASMO', 'PRIMARY_4', level, 3), 'SASMO/grade_4-5/PRIMARY_4/3')
        with self.assertRaises(ValueError):
            diagram_folder('../SASMO', 'PRIMARY_4', level, 3)


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        with patch('supabase.create_client') as create, patch('google.genai.Client'):
            self.module = importlib.import_module('ai_questions')
            self.module = importlib.reload(self.module)
            create.return_value.table.assert_not_called()
        self.review_patch = patch.object(self.module, "review_practice_set")
        self.review_patch.start()
        self.addCleanup(self.review_patch.stop)
        self.events = []
        self.fail = None
        self.duplicate = False
        self.db = MagicMock()
        self.bucket = self.db.storage.from_.return_value
        self.bucket.get_public_url.side_effect = lambda p: 'https://example.com/' + p
        self.bucket.upload.side_effect = self.upload
        self.db.table.side_effect = self.table
        self.module.supabase = self.db
        self.module.AI_AGENT = 'gemini'
        self.module.GEMINI_API_KEY = 'test-key'
        self.module.ai_client = MagicMock()
        q = dict(position=1, topic_id=1, section_name='A', question_type='INTEGER_FILL', stem_text='Count', latex_content=None,
                 chart_type='BAR', chart_data={'categories': ['A', 'B'], 'values': [2, 3]}, options_json=None,
                 correct_answer='5', points=2, penalty_points=0, difficulty_rating=1,
                 detailed_solution_latex='2+3=5', kid_friendly_hint='Add')
        plain = dict(q, position=2, chart_type=None, chart_data=None)
        self.module.ai_client.models.generate_content.return_value.text = json.dumps({'set_title': 'Test', 'total_questions': 2, 'questions': [q, plain]})

    def upload(self, *args, **kwargs):
        self.events.append(('upload', args[0]))
        if self.fail == 'upload':
            raise RuntimeError('upload failed')

    def table(self, name):
        query = MagicMock()
        state = {'op': 'select', 'payload': None}
        for method in ('select', 'eq', 'in_', 'single', 'order', 'limit'):
            getattr(query, method).return_value = query
        for op in ('insert', 'update', 'delete'):
            def action(payload=None, op=op):
                state.update(op=op, payload=payload)
                return query
            getattr(query, op).side_effect = action
        def execute():
            op, payload = state['op'], state['payload']
            self.events.append((name, op, payload))
            if op == 'delete':
                if self.fail == 'cleanup' and name == 'exam_set_questions':
                    raise RuntimeError('cleanup failed')
                return SimpleNamespace(data=[])
            if op == 'update':
                if name == 'questions' and self.fail in ('update', 'cleanup'):
                    raise RuntimeError('update failed')
                return SimpleNamespace(data=[payload])
            if op == 'insert':
                return SimpleNamespace(data=[{'id': 101}, {'id': 102}] if name == 'questions' else [{'id': 9}])
            data = {
                'certifications': {'full_name': 'SASMO', 'prompt_philosophy': 'Math', 'default_time_minutes': 90},
                'exam_levels': {'id': 14, 'target_grade_min': 4, 'target_grade_max': 4},
                'exam_sets': [{'id': 3}] if self.duplicate else [],
                'exam_structure_rules': [{'questions_count': 2, 'chart_questions_count': 1, 'chart_types': ['BAR'], 'section_name': 'A', 'question_type': 'INTEGER_FILL', 'points_per_correct': 2, 'penalty_points': 0}],
                'topics': [{'id': 1}],
            }[name]
            return SimpleNamespace(data=data)
        query.execute.side_effect = execute
        return query

    def run_generator(self):
        self.module.generate_complete_practice_set('SASMO', 'PRIMARY_4', 'Test')

    def test_upload_before_publication(self):
        self.run_generator()
        path = 'SASMO/grade_4/PRIMARY_4/9/question_101.svg'
        args, kwargs = self.bucket.upload.call_args
        self.assertEqual(args[0], path)
        ET.fromstring(args[1])
        self.assertEqual(kwargs['file_options']['content-type'], 'image/svg+xml')
        updates = [e for e in self.events if e[:2] == ('questions', 'update')]
        self.assertEqual(updates, [('questions', 'update', {'image_url': 'https://example.com/' + path})])
        self.assertEqual(self.events[-1], ('exam_sets', 'update', {'is_published': True}))
        self.bucket.remove.assert_not_called()

    def test_failed_answer_review_never_writes(self):
        self.module.review_practice_set.side_effect = ValueError('answer disagrees')
        with self.assertRaisesRegex(ValueError, 'answer disagrees'):
            self.run_generator()
        self.assertFalse(any(e[1] == 'insert' for e in self.events))
        self.bucket.upload.assert_not_called()

    def test_persists_content_topic_instead_of_position_topic(self):
        payload = json.loads(self.module.ai_client.models.generate_content.return_value.text)
        payload['questions'][1]['topic_id'] = 7
        self.module.ai_client.models.generate_content.return_value.text = json.dumps(payload)
        original_table = self.db.table.side_effect
        def table(name):
            query = original_table(name)
            if name == 'topics':
                query.execute.side_effect = lambda: SimpleNamespace(data=[{'id': 1}, {'id': 7}])
            return query
        self.db.table.side_effect = table
        self.run_generator()
        rows = next(e[2] for e in self.events if e[:2] == ('questions', 'insert'))
        self.assertEqual([q['topic_id'] for q in rows], [1, 7])

    def test_failures_cleanup_and_never_publish(self):
        for failure in ('upload', 'update', 'cleanup'):
            with self.subTest(failure=failure):
                self.setUp()
                self.fail = failure
                with self.assertRaises(RuntimeError):
                    self.run_generator()
                self.bucket.remove.assert_called_once_with(['SASMO/grade_4/PRIMARY_4/9/question_101.svg'])
                self.assertNotIn(('exam_sets', 'update', {'is_published': True}), self.events)
                self.assertIn(('questions', 'delete', None), self.events)

    def test_duplicate_stops_generation(self):
        self.duplicate = True
        with self.assertRaises(ValueError):
            self.run_generator()
        self.module.ai_client.models.generate_content.assert_not_called()
        self.bucket.upload.assert_not_called()

    def test_invalid_chart_prevents_writes(self):
        result = json.loads(self.module.ai_client.models.generate_content.return_value.text)
        result['questions'][0]['chart_data']['values'] = []
        self.module.ai_client.models.generate_content.return_value.text = json.dumps(result)
        with self.assertRaises(ValueError):
            self.run_generator()
        self.assertFalse(any(e[1] == 'insert' for e in self.events))
        self.bucket.upload.assert_not_called()
        self.assertEqual(self.module.ai_client.models.generate_content.call_count, 3)

    def test_invalid_response_retries_then_saves_once(self):
        valid_text = self.module.ai_client.models.generate_content.return_value.text
        valid = json.loads(valid_text)
        cases = []
        extra = json.loads(valid_text)
        extra['questions'].append(extra['questions'][0].copy())
        cases.append(json.dumps(extra))
        duplicate = json.loads(valid_text)
        duplicate['questions'][1]['position'] = 1
        cases.append(json.dumps(duplicate))
        wrong_type = json.loads(valid_text)
        wrong_type['questions'][1]['question_type'] = 'PROOF'
        cases.append(json.dumps(wrong_type))
        wrong_total = json.loads(valid_text)
        wrong_total['total_questions'] = 99
        cases.extend([json.dumps(wrong_total), 'invalid JSON'])
        for invalid in cases:
            with self.subTest(invalid=invalid):
                self.setUp()
                self.module.ai_client.models.generate_content.side_effect = [
                    SimpleNamespace(text=invalid), SimpleNamespace(text=valid_text),
                ]
                self.run_generator()
                self.assertEqual(self.module.ai_client.models.generate_content.call_count, 2)
                self.assertEqual(sum(e[:2] == ('questions', 'insert') for e in self.events), 1)
                call = self.module.ai_client.models.generate_content.call_args
                self.assertIn('previous attempt failed validation', call.kwargs['contents'])

    def test_retry_limit_has_no_writes(self):
        result = json.loads(self.module.ai_client.models.generate_content.return_value.text)
        result['questions'][1]['position'] = 1
        self.module.ai_client.models.generate_content.return_value.text = json.dumps(result)
        with self.assertRaisesRegex(ValueError, 'after 2 attempts'):
            self.module.generate_complete_practice_set('SASMO', 'PRIMARY_4', 'Test', max_attempts=2)
        self.assertEqual(self.module.ai_client.models.generate_content.call_count, 2)
        self.assertFalse(any(e[1] == 'insert' for e in self.events))
        self.bucket.upload.assert_not_called()

    def test_validation_log_precedes_success(self):
        with patch('builtins.print') as output:
            self.run_generator()
        messages = [str(call.args[0]) for call in output.call_args_list]
        received = next(i for i, text in enumerate(messages) if 'Received 2 questions; validating' in text)
        validated = next(i for i, text in enumerate(messages) if 'Validated 2 questions' in text)
        published = next(i for i, text in enumerate(messages) if 'Created & Published' in text)
        self.assertLess(received, validated)
        self.assertLess(validated, published)
        self.assertFalse(any('Generated 2 questions successfully' in text for text in messages))

    def test_invalid_attempt_limit_stops_before_requests(self):
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.module.generate_complete_practice_set('SASMO', 'PRIMARY_4', 'Test', max_attempts=limit)
        self.db.table.assert_not_called()

    def test_api_failure_does_not_retry(self):
        import httpx
        self.module.ai_client.models.generate_content.side_effect = httpx.HTTPStatusError(
            'quota exceeded', request=httpx.Request('POST', 'https://example.com'), response=httpx.Response(429))
        with self.assertRaises(httpx.HTTPStatusError):
            self.run_generator()
        self.assertEqual(self.module.ai_client.models.generate_content.call_count, 1)
        self.assertFalse(any(e[1] == 'insert' for e in self.events))

    def test_no_charts_needs_no_storage(self):
        result = json.loads(self.module.ai_client.models.generate_content.return_value.text)
        result['questions'][0].update(chart_type=None, chart_data=None)
        self.module.ai_client.models.generate_content.return_value.text = json.dumps(result)
        original_table = self.db.table.side_effect
        def table(name):
            query = original_table(name)
            if name == 'exam_structure_rules':
                execute = query.execute.side_effect
                def no_chart_rules():
                    response = execute()
                    response.data[0]['chart_questions_count'] = 0
                    return response
                query.execute.side_effect = no_chart_rules
            return query
        self.db.table.side_effect = table
        self.db.storage.from_.reset_mock()
        self.run_generator()
        self.db.storage.from_.assert_not_called()
        self.assertEqual(self.events[-1], ('exam_sets', 'update', {'is_published': True}))


if __name__ == '__main__':
    unittest.main()
