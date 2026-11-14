import importlib
import json
import unittest
from unittest.mock import patch

import httpx


class QuestionBatchTests(unittest.TestCase):
    def setUp(self):
        with patch('supabase.create_client'):
            self.m = importlib.import_module('ai_questions')
            self.m = importlib.reload(self.m)
        self.m.AI_AGENT = 'gemini'
        self.topics = [{'id': 1, 'title': 'Arithmetic'}, {'id': 2, 'title': 'Geometry'}]
        self.sections = [(1, 4, dict(section_name='A', question_type='INTEGER_FILL',
            points_per_correct=2, penalty_points=0, chart_questions_count=1, chart_types=['BAR'])),
            (5, 7, dict(section_name='B', question_type='INTEGER_FILL',
            points_per_correct=3, penalty_points=1, chart_questions_count=1, chart_types=['LINE']))]
        ideas = ['Count marbles after a purchase', 'Read the most popular pet from a bar chart',
                 'Find the perimeter of a square', 'Calculate elapsed journey time',
                 'Count arrangements of coloured flags', 'Compare temperatures across a week',
                 'Identify the missing term in a sequence']
        self.plan = self.m.WholeSetPlan(questions=[self.m.PlannedQuestion(
            position=i, topic_id=1 if i != 3 else 2, skill=idea,
            scenario=idea, problem_style='Word problem', difficulty_rating=i,
            chart_type={2: 'BAR', 6: 'LINE'}.get(i)) for i, idea in enumerate(ideas, 1)])
        stems = ['Lena has 12 red marbles and buys 5 more. How many marbles now?',
                 'How many children chose dogs as their favourite pet?',
                 'What is the perimeter of a square of side length 4 cm?',
                 'How long is the journey from noon to three in the afternoon?',
                 'How many ways can three different flags be ordered?',
                 'On which day is the recorded temperature the lowest?',
                 'What is the next term in the sequence 1, 4, 9, 16?']
        self.questions = {}
        for slot, stem in zip(self.plan.questions, stems):
            rule = self.sections[0 if slot.position < 5 else 1][2]
            self.questions[slot.position] = self.m.QuestionItem(
                position=slot.position, topic_id=slot.topic_id, section_name=rule['section_name'],
                question_type='INTEGER_FILL', stem_text=stem, latex_content=None,
                chart_type=slot.chart_type, chart_data=(
                    {'categories': ['Dogs', 'Cats'], 'values': [4, 2]} if slot.position == 2 else
                    {'categories': ['Monday', 'Tuesday'], 'values': [30, 29]} if slot.position == 6 else None),
                options_json=None, correct_answer='4', points=rule['points_per_correct'],
                penalty_points=rule['penalty_points'], difficulty_rating=slot.difficulty_rating,
                detailed_solution_latex='Compute the requested value.', kid_friendly_hint='Use the given data.')
        self.calls = []
        self.prompts = []
        review = patch.object(self.m, 'review_practice_set')
        self.review = review.start()
        self.addCleanup(review.stop)

    def response(self, system, user, expected_count, *, positions, set_title=None):
        self.calls.append(list(positions))
        self.prompts.append(json.JSONDecoder().raw_decode(user)[0])
        self.assertEqual(expected_count, len(positions))
        return self.m.PracticeSetSchema(set_title='Test', total_questions=len(positions),
            questions=[self.questions[p].model_copy(deep=True) for p in positions])

    def generate(self, request=None, attempts=3):
        with patch.object(self.m, 'request_practice_set', side_effect=request or self.response):
            return self.m.generate_planned_practice_set('Rules', 'Test', self.plan, self.sections,
                                                       self.topics, attempts)

    def test_global_positions_chart_data_and_answers_stay_together(self):
        result = self.generate()
        self.assertEqual(self.calls, [[1, 3, 4, 5, 7], [2, 6]])
        self.assertEqual([q.position for q in result.questions], list(range(1, 8)))
        self.assertEqual(result.total_questions, 7)
        for q in result.questions:
            self.assertEqual(q.chart_data, self.questions[q.position].chart_data)
            self.assertEqual(q.correct_answer, self.questions[q.position].correct_answer)
        self.assertEqual([q['position'] for q in self.prompts[1]['previous_questions_to_avoid']], [1, 3, 4, 5, 7])
        self.assertNotIn('correct_answer', json.dumps(self.prompts))
        self.assertEqual(len(self.m.validate_practice_set(result, 7, self.sections)), 2)
        self.assertEqual(self.review.call_count, 2)

    def test_number_variant_regenerates_only_conflicting_position(self):
        def request(*args, **kwargs):
            result = self.response(*args, **kwargs)
            if kwargs['positions'] == [1, 3, 4, 5, 7]:
                result.questions[2].stem_text = self.questions[1].stem_text.replace('12', '15').replace('5 more', '8 more')
            return result
        result = self.generate(request)
        self.assertEqual(self.calls, [[1, 3, 4, 5, 7], [4], [2, 6]])
        self.assertEqual(result.questions[3].stem_text, self.questions[4].stem_text)
        self.assertEqual([q['position'] for q in self.prompts[1]['previous_questions_to_avoid']], [1, 3, 5, 7])

    def test_within_batch_duplicate_regenerates_only_later_question(self):
        def request(*args, **kwargs):
            result = self.response(*args, **kwargs)
            if kwargs['positions'] == [1, 3, 4, 5, 7]:
                result.questions[1].stem_text = result.questions[0].stem_text
            return result
        self.generate(request)
        self.assertEqual(self.calls[:2], [[1, 3, 4, 5, 7], [3]])

    def test_duplicate_exhaustion_stops_before_persistence(self):
        self.questions[4].stem_text = self.questions[1].stem_text
        with self.assertRaisesRegex(ValueError, 'duplicates question 1'):
            self.generate(attempts=2)
        self.assertEqual(self.calls, [[1, 3, 4, 5, 7], [4]])
        self.m.supabase.rpc.assert_not_called()
        self.m.supabase.storage.from_.assert_not_called()

    def test_review_failure_retries_current_batch_only(self):
        self.review.side_effect = [None, ValueError('incorrect answer'), None, None]
        self.generate()
        self.assertEqual(self.calls, [[1, 3, 4, 5, 7], [2, 6], [2, 6]])
        self.assertEqual([q['position'] for q in self.prompts[2]['previous_questions_to_avoid']], [1, 3, 4, 5, 7])

    def test_http_failure_is_not_treated_as_a_duplicate_retry(self):
        def request(*args, **kwargs):
            self.calls.append(kwargs['positions'])
            httpx.Response(401, request=httpx.Request('POST', 'https://example.com')).raise_for_status()
        with self.assertRaises(httpx.HTTPStatusError):
            self.generate(request)
        self.assertEqual(len(self.calls), 1)
        self.m.supabase.rpc.assert_not_called()

    def test_wrong_count_and_positions_are_rejected(self):
        def request(*args, **kwargs):
            result = self.response(*args, **kwargs)
            result.questions[0].position = 99
            return result
        with self.assertRaisesRegex(ValueError, 'assigned global positions'):
            self.generate(request, attempts=2)
        self.assertEqual(self.calls, [[1, 3, 4, 5, 7], [1, 3, 4, 5, 7]])
        self.review.assert_not_called()

    def test_plan_scoring_and_chart_assignments_are_enforced(self):
        for field, value in [('chart_type', 'PIE'), ('points', 9), ('topic_id', 999),
                             ('difficulty_rating', 10), ('section_name', 'Wrong')]:
            def request(*args, **kwargs):
                result = self.response(*args, **kwargs)
                setattr(result.questions[0], field, value)
                return result
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                self.generate(request, attempts=1)

    def test_groq_413_splits_generation_without_losing_positions(self):
        self.m.AI_AGENT = 'groq'
        def request(*args, **kwargs):
            if len(kwargs['positions']) > 1:
                self.calls.append(list(kwargs['positions']))
                httpx.Response(413, request=httpx.Request('POST', 'https://api.groq.com')).raise_for_status()
            return self.response(*args, **kwargs)
        result = self.generate(request)
        self.assertEqual([q.position for q in result.questions], list(range(1, 8)))
        self.assertIn([1], self.calls)
        self.assertIn([7], self.calls)

    def test_all_three_groups_are_generated_once_and_sorted_at_end(self):
        self.sections[0][2].update(chart_questions_count=2, chart_types=['BAR', 'GEOMETRY_SVG'])
        self.plan.questions[2].chart_type = 'GEOMETRY_SVG'
        self.questions[3].chart_type = 'GEOMETRY_SVG'
        self.questions[3].chart_data = {'diagram_description': 'A square with side length 4 cm.'}
        def draw(result):
            for q in result.questions:
                if q.chart_type == 'GEOMETRY_SVG':
                    q.chart_data = {'svg': "<svg viewBox='0 0 10 10'><rect width='4' height='4'/></svg>"}
            return {}
        with patch.object(self.m, 'generate_geometry_diagrams', side_effect=draw):
            result = self.generate()
        self.assertEqual(self.calls, [[1, 4, 5, 7], [2, 6], [3]])
        self.assertEqual([p['generation_group'] for p in self.prompts], ['text-only', 'chart', 'geometry'])
        self.assertEqual([q.position for q in result.questions], list(range(1, 8)))
        self.assertIn('svg', result.questions[2].chart_data)

    def test_empty_groups_make_no_requests(self):
        for _, _, rule in self.sections:
            rule['chart_questions_count'] = 0
        for slot in self.plan.questions:
            slot.chart_type = None
            self.questions[slot.position].chart_type = None
            self.questions[slot.position].chart_data = None
        self.generate()
        self.assertEqual(self.calls, [list(range(1, 8))])

    def test_output_limit_splits_only_the_affected_group(self):
        def request(*args, **kwargs):
            if kwargs['positions'] == [1, 3, 4, 5, 7]:
                self.calls.append(kwargs['positions'])
                raise self.m.ResponseTokenLimitError('output limit')
            return self.response(*args, **kwargs)
        self.generate(request)
        self.assertEqual(self.calls, [[1, 3, 4, 5, 7], [1, 3], [4, 5, 7], [2, 6]])

    def test_single_question_limit_stops_without_repeating_accepted_positions(self):
        def request(*args, **kwargs):
            if len(kwargs['positions']) > 1 or kwargs['positions'] == [3]:
                self.calls.append(kwargs['positions'])
                raise self.m.ResponseTokenLimitError('output limit')
            return self.response(*args, **kwargs)
        with self.assertRaises(self.m.ResponseTokenLimitError):
            self.generate(request)
        self.assertEqual(self.calls.count([1]), 1)
        self.assertEqual(self.calls.count([3]), 1)
        self.m.supabase.rpc.assert_not_called()

    def test_gemini_413_splits_but_generic_400_does_not(self):
        def request(*args, **kwargs):
            if kwargs['positions'] == [1, 3, 4, 5, 7]:
                self.calls.append(kwargs['positions'])
                raise self.m.genai_errors.ClientError(413, {'error': {'message': 'Too large'}})
            return self.response(*args, **kwargs)
        self.generate(request)
        self.assertEqual(self.calls, [[1, 3, 4, 5, 7], [1, 3], [4, 5, 7], [2, 6]])
        self.calls.clear()
        with patch.object(self.m, 'request_practice_set', side_effect=self.m.genai_errors.ClientError(
                400, {'error': {'message': 'Invalid argument'}})) as request:
            with self.assertRaises(self.m.genai_errors.ClientError):
                self.m.generate_planned_practice_set('Rules', 'Test', self.plan, self.sections, self.topics, 3)
        request.assert_called_once()

    def test_review_size_error_does_not_split_or_repeat_generation(self):
        self.review.side_effect = httpx.HTTPStatusError('too large',
            request=httpx.Request('POST', 'https://example.com'), response=httpx.Response(413))
        with self.assertRaises(httpx.HTTPStatusError):
            self.generate()
        self.assertEqual(self.calls, [[1, 3, 4, 5, 7]])

    def test_cross_group_near_duplicate_is_retried(self):
        self.questions[1].stem_text = ('Lena is organizing a collection of coloured marbles for a school activity. '
            'She starts with twelve red marbles and receives five more from a friend. '
            'She keeps every marble in a single container and does not give any away. '
            'How many marbles does Lena have in her container after receiving the gift?')
        def request(*args, **kwargs):
            result = self.response(*args, **kwargs)
            if kwargs['positions'] == [2, 6]:
                result.questions[0].stem_text = self.questions[1].stem_text
            return result
        self.generate(request)
        self.assertEqual(self.calls, [[1, 3, 4, 5, 7], [2, 6], [2]])

    def test_recovered_groq_arrays_still_pass_through_duplicate_checks_and_review(self):
        self.m.AI_AGENT = 'groq'
        self.m.GROQ_API_KEY = 'test-key'
        def post(url, **kwargs):
            prompt = json.JSONDecoder().raw_decode(kwargs['json']['messages'][1]['content'])[0]
            positions = [slot['position'] for slot in prompt['assigned_questions']]
            self.calls.append(positions)
            return httpx.Response(400, request=httpx.Request('POST', url), json={'error': {
                'code': 'json_validate_failed',
                'message': "Generated JSON does not match the expected schema. Error: jsonschema: '' "
                           'does not validate with /type: expected object, but got array',
                'failed_generation': json.dumps([self.questions[p].model_dump() for p in positions]),
            }})
        with patch.object(self.m.httpx, 'post', side_effect=post):
            result = self.m.generate_planned_practice_set('Rules', 'Test', self.plan,
                                                         self.sections, self.topics, 2)
        self.assertEqual(self.calls, [[1, 3, 4, 5, 7], [2, 6]])
        self.assertEqual([q.position for q in result.questions], list(range(1, 8)))
        self.assertEqual(self.review.call_count, 2)
        self.assertEqual(result.questions[1].chart_data, self.questions[2].chart_data)
        self.calls.clear()
        self.questions[4].stem_text = self.questions[1].stem_text
        with patch.object(self.m.httpx, 'post', side_effect=post):
            with self.assertRaisesRegex(ValueError, 'duplicates question 1'):
                self.m.generate_planned_practice_set('Rules', 'Test', self.plan,
                                                     self.sections, self.topics, 2)
        self.assertEqual(self.calls, [[1, 3, 4, 5, 7], [4]])
        self.m.supabase.rpc.assert_not_called()

    def test_outer_math_delimiters_do_not_regenerate_questions_for_either_provider(self):
        formulas = {1: ('$12+5$', '12+5'), 2: ('$$4$$', '4'),
                    3: (r'\[4*4\]', '4*4'), 4: (r'\(3\)', '3')}
        for position, (wrapped, _) in formulas.items():
            self.questions[position].latex_content = wrapped
        for provider in ('groq', 'gemini'):
            self.m.AI_AGENT = provider
            self.calls.clear()
            with self.subTest(provider=provider):
                result = self.generate()
                self.assertEqual(self.calls, [[1, 3, 4, 5, 7], [2, 6]])
                for position, (_, bare) in formulas.items():
                    self.assertEqual(result.questions[position - 1].latex_content, bare)

    def test_question_comparison_handles_formatting_numbers_and_similar_wording(self):
        compare = self.m.similar_question_text
        self.assertTrue(compare('What is $2+3$?', 'WHAT is 2 + 3?'))
        self.assertTrue(compare('Find 12 + 15.', 'Find 20 + 18.'))
        self.assertFalse(compare('Find 12 + 15.', 'Find 12 - 15.'))
        self.assertTrue(compare(self.questions[1].stem_text,
                                self.questions[1].stem_text.replace('Lena', 'Mina')))
        self.assertFalse(compare(self.questions[1].stem_text, self.questions[4].stem_text))

    def test_invalid_plans_are_rejected(self):
        for change in ('position', 'topic', 'chart', 'idea'):
            plan = self.plan.model_copy(deep=True)
            if change == 'position': plan.questions[1].position = 1
            if change == 'topic': plan.questions[0].topic_id = 999
            if change == 'chart': plan.questions[1].chart_type = None
            if change == 'idea': plan.questions[1].scenario = plan.questions[0].scenario
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.m.validate_whole_set_plan(plan, self.sections, self.topics)

    def test_planner_retries_invalid_plan_and_keeps_prompt_compact(self):
        bad = self.plan.model_dump()
        bad['questions'][0]['topic_id'] = 999
        topics = [dict(t, unused_metadata='x' * 10000) for t in self.topics]
        with patch.object(self.m, 'request_structured_json', side_effect=[bad, self.plan.model_dump()]) as request:
            plan = self.m.request_whole_set_plan('Grade 4', self.sections, topics, 2)
        self.assertEqual(len(plan.questions), 7)
        self.assertEqual(request.call_count, 2)
        self.assertNotIn('unused_metadata', request.call_args.args[1])
        self.assertIn('Correct the previous plan', request.call_args.args[1])
        self.assertEqual(request.call_args.args[3]['json_schema']['name'], 'whole_set_plan')

    def test_request_schema_allows_later_global_positions(self):
        payload = self.m.PracticeSetSchema(set_title='Test', total_questions=1,
                                          questions=[self.questions[7]]).model_dump()
        with patch.object(self.m, 'request_structured_json', return_value=payload) as request:
            self.m.request_practice_set('Rules', 'Generate', 1, positions=[7])
        gemini, groq = request.call_args.args[2:]
        for schema in (gemini, groq['json_schema']['schema']):
            position = schema['$defs']['QuestionItem']['properties']['position']
            self.assertEqual((position['minimum'], position['maximum']), (7, 7))
            self.assertEqual(schema['properties']['questions']['maxItems'], 1)
        self.assertEqual(groq['json_schema']['schema']['$defs']['QuestionItem']['properties']['position']['enum'], [7])


if __name__ == '__main__':
    unittest.main()
