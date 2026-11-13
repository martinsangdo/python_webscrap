import importlib
import json
import unittest
from unittest.mock import patch


class QualityTests(unittest.TestCase):
    def setUp(self):
        with patch('supabase.create_client'):
            self.module = importlib.import_module('ai_questions')
        self.q = self.module.QuestionItem(
            position=1, topic_id=4, section_name='A', question_type='MCQ_4_OPTION',
            stem_text='A toy costs 12 dollars. You pay 20 dollars. How much change do you get?',
            latex_content=None, chart_type=None, chart_data=None,
            options_json={'A': '6 dollars', 'B': '8 dollars', 'C': '10 dollars', 'D': '12 dollars'},
            correct_answer='B', points=2, penalty_points=0, difficulty_rating=1,
            detailed_solution_latex='$20-12=8$. The answer is B: 8 dollars.',
            kid_friendly_hint='Subtract the cost from the amount paid.',
        )
        self.topics = [{'id': 4, 'title': 'Arithmetic'}, {'id': 5, 'title': 'Word Problems'}]
        self.review = {'questions': [{
            'position': 1, 'topic_id': 5, 'correct_answer': 'B', 'unambiguous': True,
            'detailed_solution_latex': '$20-12=8$. You receive 8 dollars, option B.',
        }]}

    def result(self):
        return self.module.PracticeSetSchema(set_title='Test', total_questions=1, questions=[self.q])

    def test_currency_words_and_real_math_are_valid(self):
        self.q.stem_text += ' Calculate $20 - 12$.'
        self.module.validate_question_content(self.q, {4})

    def test_currency_in_every_display_field_is_rejected(self):
        for field in ('stem_text', 'latex_content', 'detailed_solution_latex', 'kid_friendly_hint'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'currency'):
                self.module.validate_question_content(self.q.model_copy(update={field: r'$\$12$'}), {4})
        self.q.options_json['B'] = r'$\$8$'
        with self.assertRaisesRegex(ValueError, 'currency'):
            self.module.validate_question_content(self.q, {4})

    def test_invalid_answers_options_topics_and_delimiters(self):
        for update in (
            {'correct_answer': 'E'}, {'correct_answer': '8'},
            {'options_json': {'A': '1', 'B': '1', 'C': '2', 'D': '3'}},
            {'options_json': {'A': '1'}}, {'topic_id': 999},
            {'stem_text': 'Compute $2+3'}, {'latex_content': '$2+3$'},
            {'question_type': 'INTEGER_FILL', 'options_json': None, 'correct_answer': '1.5'},
        ):
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.module.validate_question_content(self.q.model_copy(update=update), {4})

    def test_blind_review_withholds_key_solution_hint_and_topic(self):
        result = self.result()
        with patch.object(self.module, 'request_structured_json', return_value=self.review) as request:
            self.module.review_practice_set(result, self.topics)
        sent = json.loads(request.call_args.args[1])['questions'][0]
        for key in ('correct_answer', 'detailed_solution_latex', 'kid_friendly_hint', 'topic_id'):
            self.assertNotIn(key, sent)
        self.assertEqual(sent['options_json'], self.q.options_json)
        self.assertEqual(result.questions[0].topic_id, 5)
        self.assertEqual(result.questions[0].detailed_solution_latex,
                         self.review['questions'][0]['detailed_solution_latex'])

    def test_wrong_key_ambiguity_unknown_topic_and_bad_review_format_rejected(self):
        for update in ({'correct_answer': 'A'}, {'unambiguous': False},
                       {'topic_id': 999}, {'position': 2},
                       {'detailed_solution_latex': r'Get $\$8$.'}):
            review = {'questions': [dict(self.review['questions'][0], **update)]}
            with self.subTest(update=update), patch.object(self.module, 'request_structured_json', return_value=review):
                with self.assertRaises(ValueError):
                    self.module.review_practice_set(self.result(), self.topics)

    def test_review_requires_exact_coverage(self):
        for questions in ([], self.review['questions'] * 2):
            with patch.object(self.module, 'request_structured_json', return_value={'questions': questions}):
                with self.assertRaises(ValueError):
                    self.module.review_practice_set(self.result(), self.topics)


if __name__ == '__main__':
    unittest.main()
