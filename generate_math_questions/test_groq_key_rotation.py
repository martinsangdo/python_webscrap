import importlib
import unittest
from unittest.mock import patch

import httpx


class GroqKeyRotationTests(unittest.TestCase):
    def setUp(self):
        with patch('supabase.create_client'):
            self.module = importlib.import_module('ai_questions')
        for name, value in [('AI_AGENT', 'groq'), ('GROQ_API_KEYS', ['one', 'two']),
                            ('groq_api_key_index', 0)]:
            patcher = patch.object(self.module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(self.module, 'get_certification_ids', return_value=['TEST'])
        patcher.start()
        self.addCleanup(patcher.stop)

    def error(self, status=429, host='api.groq.com'):
        response = httpx.Response(status, request=httpx.Request('POST', f'https://{host}/test'))
        return httpx.HTTPStatusError('limit', request=response.request, response=response)

    def test_rotates_and_retries_same_set(self):
        for period in ('daily', 'minute'):
            with self.subTest(period=period):
                self.module.groq_api_key_index = 1
                indices = []
                def generate(**kwargs):
                    indices.append(self.module.groq_api_key_index)
                    if len(indices) == 1:
                        raise self.error()
                with patch.object(self.module, 'generate_complete_practice_set', side_effect=generate) as call:
                    self.module.main()
                self.assertEqual(indices, [1, 0])
                self.assertEqual(call.call_args_list[0], call.call_args_list[1])

    def test_stops_when_all_keys_limited(self):
        with patch.object(self.module, 'generate_complete_practice_set', side_effect=self.error()) as call:
            with self.assertRaises(httpx.HTTPStatusError):
                self.module.main()
        self.assertEqual(call.call_count, 2)

    def test_does_not_rotate_unrelated_errors_or_single_key(self):
        for provider, keys, error in [
            ('groq', ['one'], self.error()),
            ('groq', ['one', 'two'], self.error(401)),
            ('groq', ['one', 'two'], self.error(host='database.example')),
            ('gemini', ['one', 'two'], self.error()),
        ]:
            with self.subTest(provider=provider, keys=keys, error=error):
                self.module.AI_AGENT = provider
                self.module.GROQ_API_KEYS = keys
                with patch.object(self.module, 'generate_complete_practice_set', side_effect=error) as call:
                    with self.assertRaises(httpx.HTTPStatusError):
                        self.module.main()
                call.assert_called_once()
                self.assertEqual(self.module.groq_api_key_index, 0)


if __name__ == '__main__':
    unittest.main()
