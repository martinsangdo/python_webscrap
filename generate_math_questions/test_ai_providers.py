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

    @patch('ai_questions.httpx.post')
    def test_groq_rejects_invalid_or_truncated_output(self, post):
        self.module.AI_AGENT = 'groq'
        for content, reason in [('', 'stop'), ('{}', 'stop'), ('not json', 'stop'), ('{}', 'length')]:
            post.return_value = self.response(content, reason)
            with self.subTest(content=content, reason=reason), self.assertRaises(ValueError):
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
    def test_latex_and_svg_survive_strict_response(self, post):
        self.module.AI_AGENT = 'groq'
        question = dict(position=1, topic_id=1, section_name='Test', question_type='INTEGER_FILL',
            stem_text='Find the radius.', latex_content=r'$\\frac{4}{2}$',
            chart_type='GEOMETRY_SVG', chart_data={'svg': '<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="2"/></svg>'},
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
