import importlib
import json
import unittest
from unittest.mock import MagicMock, patch

import httpx


class ProviderTests(unittest.TestCase):
    def setUp(self):
        with patch('supabase.create_client'), patch('google.genai.Client') as client:
            self.module = importlib.import_module('ai_questions')
            self.module = importlib.reload(self.module)
            client.assert_not_called()
        self.module.GROQ_API_KEY = 'test-groq-key'
        self.module.GEMINI_API_KEY = 'test-gemini-key'
        self.payload = {'set_title': 'Test', 'total_questions': 0, 'questions': []}

    def response(self, content=None, reason='stop'):
        response = MagicMock()
        response.json.return_value = {'choices': [{'finish_reason': reason, 'message': {'content': json.dumps(self.payload) if content is None else content}}]}
        return response

    @patch('ai_questions.httpx.post')
    def test_groq(self, post):
        self.module.AI_AGENT = 'groq'
        self.module.GEMINI_API_KEY = None
        post.return_value = self.response()
        with patch('ai_questions.genai.Client') as gemini:
            result = self.module.request_practice_set('Rules', 'Generate')
            gemini.assert_not_called()
        self.assertEqual(result.set_title, 'Test')
        args, kwargs = post.call_args
        self.assertEqual(args[0], 'https://api.groq.com/openai/v1/chat/completions')
        self.assertEqual(kwargs['json']['model'], self.module.GROQ_MODEL)
        self.assertEqual(kwargs['json']['response_format']['type'], 'json_schema')
        self.assertTrue(kwargs['json']['response_format']['json_schema']['strict'])
        self.assertIn('JSON Schema', kwargs['json']['messages'][0]['content'])

    @patch('ai_questions.httpx.post')
    def test_gemini(self, post):
        self.module.AI_AGENT = 'gemini'
        self.module.GROQ_API_KEY = None
        with patch('ai_questions.genai.Client') as client:
            client.return_value.models.generate_content.return_value.text = json.dumps(self.payload)
            result = self.module.request_practice_set('Rules', 'Generate')
            client.assert_called_once_with(api_key='test-gemini-key')
        self.assertEqual(result.total_questions, 0)
        post.assert_not_called()

    def test_gemini_uses_explicit_schema_and_numeric_count_bounds(self):
        self.module.AI_AGENT = 'gemini'
        with patch('ai_questions.genai.Client') as client:
            client.return_value.models.generate_content.return_value.text = json.dumps(self.payload)
            self.module.request_practice_set('Rules', 'Generate', expected_count=0)
        config = client.return_value.models.generate_content.call_args.kwargs['config']
        schema = config.response_json_schema
        count = schema['properties']['total_questions']
        self.assertNotIn('enum', count)
        self.assertEqual((count['minimum'], count['maximum']), (0, 0))
        question = schema['$defs']['QuestionItem']['properties']
        for field in ('chart_data', 'options_json'):
            for variant in question[field]['anyOf']:
                if variant.get('type') == 'object':
                    self.assertTrue(variant['properties'])
                    self.assertIs(variant['additionalProperties'], False)
        self.assertEqual(self.module.groq_response_format(3)['json_schema']['schema']
                         ['properties']['total_questions']['enum'], [3])

    def test_gemini_removes_array_bounds_without_mutating_shared_schema(self):
        self.module.AI_AGENT = 'gemini'
        schema = self.module.gemini_practice_set_json_schema(30)
        original = json.loads(json.dumps(schema))
        with patch('ai_questions.genai.Client') as client:
            client.return_value.models.generate_content.return_value.text = '{}'
            self.module.request_structured_json('Rules', 'Generate', schema, {})
        sent = client.return_value.models.generate_content.call_args.kwargs['config'].response_json_schema
        self.assertNotIn('minItems', sent['properties']['questions'])
        self.assertNotIn('maxItems', sent['properties']['questions'])
        self.assertEqual(schema, original)
        review = {'properties': {'questions': {'type': 'array', 'minItems': 30,
                  'maxItems': 30, 'items': {'type': 'object'}}}}
        self.assertNotIn('maxItems', self.module.gemini_wire_schema(review)['properties']['questions'])
        self.assertEqual(review['properties']['questions']['maxItems'], 30)

    @patch('ai_questions.httpx.post')
    def test_groq_rejects_invalid_or_truncated_output(self, post):
        self.module.AI_AGENT = 'groq'
        for content, reason in [('', 'stop'), ('{}', 'stop'), ('not json', 'stop'), ('{}', 'length')]:
            post.return_value = self.response(content, reason)
            with self.subTest(content=content, reason=reason), self.assertRaises(ValueError):
                self.module.request_practice_set('Rules', 'Generate')

    @patch('ai_questions.httpx.post')
    def test_groq_length_finish_is_an_explicit_output_limit(self, post):
        self.module.AI_AGENT = 'groq'
        post.return_value = self.response(reason='length')
        with self.assertRaises(self.module.ResponseTokenLimitError):
            self.module.request_practice_set('Rules', 'Generate')

    def test_gemini_max_tokens_is_detected_before_parsing_partial_json(self):
        from types import SimpleNamespace
        self.module.AI_AGENT = 'gemini'
        with patch('ai_questions.genai.Client') as client:
            client.return_value.models.generate_content.return_value = SimpleNamespace(
                text='{incomplete', candidates=[SimpleNamespace(
                    finish_reason=self.module.types.FinishReason.MAX_TOKENS)])
            with self.assertRaises(self.module.ResponseTokenLimitError):
                self.module.request_practice_set('Rules', 'Generate')

    @patch('ai_questions.httpx.post')
    def test_http_failure_does_not_fallback(self, post):
        self.module.AI_AGENT = 'groq'
        post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError('rate limit', request=httpx.Request('POST', 'https://api.groq.com'), response=httpx.Response(429))
        with patch('ai_questions.genai.Client') as client, self.assertRaises(httpx.HTTPStatusError):
            self.module.request_practice_set('Rules', 'Generate')
        client.assert_not_called()

    @patch('ai_questions.httpx.post')
    def test_model_error_includes_diagnostic_and_redacts_key(self, post):
        self.module.AI_AGENT = 'groq'
        post.return_value = httpx.Response(
            404,
            request=httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions'),
            json={'error': {'message': 'Model unavailable test-groq-key'}},
        )
        with self.assertRaises(httpx.HTTPStatusError) as caught:
            self.module.request_practice_set('Rules', 'Generate')
        self.assertIn('Model unavailable', str(caught.exception))
        self.assertIn('Check GROQ_MODEL', str(caught.exception))
        self.assertNotIn('test-groq-key', str(caught.exception))

    @patch('ai_questions.httpx.post')
    def test_provider_output_validation_error_is_retryable(self, post):
        self.module.AI_AGENT = 'groq'
        post.return_value = httpx.Response(400,
            request=httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions'),
            json={'error': {'code': 'json_validate_failed', 'message': 'Generated JSON does not match the expected schema'}})
        with self.assertRaisesRegex(ValueError, 'Groq output failed validation'):
            self.module.request_practice_set('Rules', 'Generate')

    def root_array_error(self, failed_generation, *, message=None):
        return httpx.Response(400,
            request=httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions'),
            json={'error': {'code': 'json_validate_failed',
                'message': message or ("Generated JSON does not match the expected schema. "
                    "Error: jsonschema: '' does not validate with /type: expected object, but got array"),
                'failed_generation': failed_generation}})

    def recovery_question(self, position=4):
        return dict(position=position, topic_id=1, section_name='A', question_type='MCQ_4_OPTION',
            stem_text='Find the sum of two and three.', latex_content=None,
            chart_type=None, chart_data=None, options_json={'A': '3', 'B': '4', 'C': '5', 'D': '6', 'E': None},
            correct_answer='C', points=2, penalty_points=0, difficulty_rating=1,
            detailed_solution_latex='The sum is five.', kid_friendly_hint='Add the quantities.')

    @patch('ai_questions.httpx.post')
    def test_recovers_complete_root_array_using_requested_title_and_positions(self, post):
        self.module.AI_AGENT = 'groq'
        questions = [self.recovery_question(4), self.recovery_question(7)]
        post.return_value = self.root_array_error(json.dumps(questions))
        with patch('builtins.print') as output:
            result = self.module.request_practice_set('Rules', 'Generate', 2,
                                                      positions=[4, 7], set_title='Requested title')
        self.assertEqual(result.set_title, 'Requested title')
        self.assertEqual(result.total_questions, 2)
        self.assertEqual([q.position for q in result.questions], [4, 7])
        self.assertNotIn('E', result.questions[0].options_json)
        self.assertEqual(result.questions[0].correct_answer, 'C')
        post.assert_called_once()
        sent = post.call_args.kwargs['json']
        self.assertIn('Never return a bare array', sent['messages'][0]['content'])
        self.assertTrue(sent['response_format']['json_schema']['strict'])
        self.assertNotIn(questions[0]['stem_text'], str(output.call_args_list))

    @patch('ai_questions.httpx.post')
    def test_array_recovery_rejects_missing_malformed_incomplete_or_invalid_data(self, post):
        self.module.AI_AGENT = 'groq'
        q = self.recovery_question()
        cases = [None, '[broken', json.dumps([]), json.dumps([q, q]),
                 json.dumps([dict(q, position=9)]), json.dumps([{'position': 4}]),
                 json.dumps({'questions': [q]}), json.dumps([dict(q, chart_type='UNKNOWN')])]
        for failed in cases:
            post.return_value = self.root_array_error(failed)
            with self.subTest(failed=failed), self.assertRaises(self.module.GroqOutputValidationError):
                self.module.request_practice_set('Rules', 'Generate', 1, positions=[4], set_title='Test')

    @patch('ai_questions.httpx.post')
    def test_array_recovery_is_limited_to_top_level_shape_error(self, post):
        self.module.AI_AGENT = 'groq'
        failed = json.dumps([self.recovery_question()])
        for message in ('Generated JSON does not match the expected schema.',
                        "Generated JSON does not match the expected schema. Error: jsonschema: '/questions/0' "
                        'does not validate with /type: expected object, but got array'):
            post.return_value = self.root_array_error(failed, message=message)
            with self.subTest(message=message), self.assertRaises(self.module.GroqOutputValidationError):
                self.module.request_practice_set('Rules', 'Generate', 1, positions=[4], set_title='Test')
        post.return_value = self.root_array_error(failed)
        with self.assertRaises(self.module.GroqOutputValidationError):
            self.module.request_practice_set('Rules', 'Generate', 1, positions=[4])

    @patch('ai_questions.httpx.post')
    def test_invalid_config(self, post):
        for provider in ('unsupported', 'groq', 'gemini'):
            self.module.AI_AGENT = provider
            self.module.GROQ_API_KEY = None
            self.module.GEMINI_API_KEY = None
            with self.subTest(provider=provider), self.assertRaises(ValueError):
                self.module.request_practice_set('Rules', 'Generate')
        post.assert_not_called()

    def test_env_selection_normalized(self):
        with patch('dotenv.load_dotenv'), patch.dict('os.environ', {'AI_AGENT': ' GROQ ', 'GROQ_MODEL': 'custom-model'}), patch('supabase.create_client'):
            module = importlib.reload(self.module)
            self.assertEqual(module.AI_AGENT, 'groq')
            self.assertEqual(module.GROQ_MODEL, 'custom-model')

    def test_strict_schema_closes_every_object(self):
        schema = self.module.groq_response_format()['json_schema']['schema']
        def check(node):
            if isinstance(node, dict):
                if node.get('type') == 'object':
                    self.assertIs(node['additionalProperties'], False)
                    self.assertEqual(set(node['required']), set(node['properties']))
                for value in node.values():
                    check(value)
            elif isinstance(node, list):
                for value in node:
                    check(value)
        check(schema)
        # Provider-specific constraints must not mutate Gemini's schema.
        original = self.module.PracticeSetSchema.model_json_schema()
        self.assertNotIn('additionalProperties', original)

    def test_expected_count_constrains_both_provider_schemas(self):
        for schema in (self.module.practice_set_json_schema(25),
                       self.module.groq_response_format(25)['json_schema']['schema']):
            self.assertEqual(schema['properties']['questions']['minItems'], 25)
            self.assertEqual(schema['properties']['questions']['maxItems'], 25)
            self.assertEqual(schema['properties']['total_questions']['enum'], [25])
        self.assertNotIn('minItems', self.module.practice_set_json_schema()['properties']['questions'])

    @patch('ai_questions.httpx.post')
    def test_latex_and_geometry_description_survive_strict_response(self, post):
        self.module.AI_AGENT = 'groq'
        question = dict(position=1, topic_id=1, section_name='Test', question_type='INTEGER_FILL',
            stem_text='Find the radius.', latex_content=r'$\\frac{4}{2}$',
            chart_type='GEOMETRY_SVG', chart_data={'diagram_description': 'A circle with centre O and diameter 4 cm.'},
            options_json=None, correct_answer='2', points=2, penalty_points=0,
            difficulty_rating=1, detailed_solution_latex=r'$\\frac{4}{2}=2$', kid_friendly_hint='Halve it.')
        self.payload.update(total_questions=1, questions=[question])
        post.return_value = self.response()
        result = self.module.request_practice_set('Rules', 'Generate')
        self.assertEqual(result.questions[0].chart_data, question['chart_data'])
        self.assertEqual(result.questions[0].latex_content, question['latex_content'])
        question.update(question_type='MCQ_4_OPTION', options_json={
            'A': '1', 'B': '2', 'C': '3', 'D': '4', 'E': None,
        })
        post.return_value = self.response()
        result = self.module.request_practice_set('Rules', 'Generate')
        self.assertEqual(set(result.questions[0].options_json), set('ABCD'))

    def rate_limit_response(self, message='Please try again in 22.8825s.', headers=None):
        return httpx.Response(429, headers=headers or {},
            request=httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions'),
            json={'error': {'message': message}})

    @patch('ai_questions.time.sleep')
    @patch('ai_questions.httpx.post')
    def test_rate_limit_retries_identical_request_then_succeeds(self, post, sleep):
        self.module.AI_AGENT = 'groq'
        post.side_effect = [self.rate_limit_response(), self.response()]
        result = self.module.request_practice_set('Rules', 'Generate')
        self.assertEqual(result.set_title, 'Test')
        sleep.assert_called_once_with(23.8825)
        self.assertEqual(post.call_args_list[0], post.call_args_list[1])

    @patch('ai_questions.time.sleep')
    @patch('ai_questions.httpx.post')
    def test_retry_after_header_takes_precedence(self, post, sleep):
        self.module.AI_AGENT = 'groq'
        post.side_effect = [self.rate_limit_response(headers={'retry-after': '25'}), self.response()]
        self.module.request_practice_set('Rules', 'Generate')
        sleep.assert_called_once_with(26)

    @patch('ai_questions.time.sleep')
    @patch('ai_questions.httpx.post')
    def test_repeated_rate_limits_are_bounded(self, post, sleep):
        self.module.AI_AGENT = 'groq'
        post.return_value = self.rate_limit_response(headers={'retry-after': '1'})
        with self.assertRaisesRegex(httpx.HTTPStatusError, 'retry budget'):
            self.module.request_practice_set('Rules', 'Generate')
        self.assertEqual(post.call_count, 6)
        self.assertEqual(sleep.call_count, 5)

    @patch('ai_questions.time.sleep')
    @patch('ai_questions.httpx.post')
    def test_long_rate_limit_does_not_retry_early(self, post, sleep):
        self.module.AI_AGENT = 'groq'
        post.return_value = self.rate_limit_response('Please try again in 1h2m3s.')
        with self.assertRaises(httpx.HTTPStatusError):
            self.module.request_practice_set('Rules', 'Generate')
        post.assert_called_once()
        sleep.assert_not_called()

    @patch('ai_questions.time.sleep')
    @patch('ai_questions.httpx.post')
    def test_cumulative_wait_budget(self, post, sleep):
        self.module.AI_AGENT = 'groq'
        post.return_value = self.rate_limit_response(headers={'retry-after': '100'})
        with self.assertRaises(httpx.HTTPStatusError):
            self.module.request_practice_set('Rules', 'Generate')
        self.assertEqual(post.call_count, 3)
        self.assertEqual(sum(c.args[0] for c in sleep.call_args_list), 202)
        self.assertTrue(all(c.args[0] <= 60 for c in sleep.call_args_list))

    def test_malformed_retry_metadata_uses_backoff(self):
        response = self.rate_limit_response('No retry hint', headers={'retry-after': 'nan'})
        self.assertEqual(self.module.groq_retry_delay(response, 2), 8)
        response = self.rate_limit_response('Please try again in 1m2.5s.', headers={'retry-after': '-1'})
        self.assertEqual(self.module.groq_retry_delay(response, 0), 63.5)

    @patch('ai_questions.time.sleep')
    @patch('ai_questions.httpx.post')
    def test_non_rate_limit_errors_are_not_retried(self, post, sleep):
        self.module.AI_AGENT = 'groq'
        for status in (400, 401, 403, 404, 500):
            post.reset_mock()
            post.return_value = httpx.Response(status,
                request=httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions'),
                json={'error': {'message': 'error'}})
            with self.subTest(status=status), self.assertRaises(httpx.HTTPStatusError):
                self.module.request_practice_set('Rules', 'Generate')
            post.assert_called_once()
        sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
