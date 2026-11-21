import importlib
import json
import unittest
from unittest.mock import patch


class LatexValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch('supabase.create_client'), patch('dotenv.load_dotenv'):
            cls.module = importlib.import_module('ai_questions')

    def check(self, text, bare=False):
        self.module.validate_latex_field(text, field='hint', position=3, bare=bare)

    def test_supported_formulas(self):
        for text in (
            r'Choose $\binom{7}{3}=\frac{7!}{3!\,4!}=35$.',
            r'Let $R_{n}=\frac{10^{n}-1}{9}$.',
            r'$\sqrt[3]{8}=2$ and $a\neq b$.',
            r'$\left(\frac{1}{2}\right)$',
            r'$\text{area}=12\mathrm{cm}^{2}$',
            'First $x=1$.\nThen $y=2$.',
        ):
            with self.subTest(text=text):
                self.check(text)
        self.check(r'\frac{10^{n}-1}{9}', bare=True)

    def test_solution_ellipsis_and_ceiling_commands(self):
        for text in (
            r'Continue the sequence $1, 2, \dots, 10$.',
            r'Round up: $\lceil\frac{7}{3}\rceil=3$.',
            r'Round up: $\left\lceil\frac{7}{3}\right\rceil=3$.',
        ):
            with self.subTest(text=text):
                q = self.question(detailed_solution_latex=text)
                self.module.validate_question_content(q, {4})
        for command in ('dots', 'lceil', 'rceil'):
            self.assertIn(command, self.module.LATEX_COMMANDS)
            with self.subTest(overescaped=command):
                with self.assertRaisesRegex(ValueError, 'unsupported or overescaped'):
                    self.check('$' + '\\\\' + command + '$')

    def test_answer_blanks_pass_unchanged_without_ai_repair(self):
        for blank in ('__', '____', r'\_\_', r'\_\_\_\_'):
            text = f'Recognize the rule in the sequence: 5, 10, 15, {blank}. What number comes next?'
            q = self.question(stem_text=text)
            before = q.model_dump()
            with self.subTest(blank=blank), patch.object(self.module, 'request_structured_json') as request:
                self.module.validate_generated_question_content(q, {4})
                request.assert_not_called()
            self.assertEqual(q.model_dump(), before)
            self.check(f'Fill in ({blank}): $2+3$ equals {blank}.')

    def test_answer_blanks_do_not_hide_latex_outside_math(self):
        for text in (r'Find x_2.', r'Find x__2.', r'Find x__.',
                     r'Find x\_\_2.', r'Find __x.',
                     r'Fill __ with \frac{1}{2}.', r'Fill __ with x^{2}.',
                     r'Fill \_\_ with \unknown{x}.'):
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, 'LaTeX outside math'):
                    self.check(text)
        with self.assertRaises(ValueError):
            self.check('$__$')

    def test_malformed_content_rejected_with_location(self):
        for text in (
            r'6\times4', r'Let \(n\) be odd.', r'\text{Explanation}',
            r'$\\frac{1}{2}$', r'$\begin{aligned}a&=1\end{aligned}$',
            r'$\frac{1}$', r'$\frac{}{2}$', r'$\sqrt$',
            r'$x_{2$', r'$x} + {y$', r'$$x$$', '$x', '$$',
            r'$\unknown{x}$', r'$x^$', r'$x&=2$',
            r'$\right)$', r'$\left(x$',
            'Bad \x0crac{1}{2}', r'Line\nNext', r'$\newline$',
        ):
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, 'Question 3, hint:'):
                    self.check(text)

    def question(self, **updates):
        from test_question_quality import QualityTests
        fixture = QualityTests()
        fixture.setUp()
        return fixture.q.model_copy(deep=True, update=updates)

    def test_matching_outer_delimiters_are_removed_then_validated(self):
        expression = r'\frac{1}{2}+x^{2}'
        for opening, closing in (('$', '$'), ('$$', '$$'), (r'\(', r'\)'), (r'\[', r'\]')):
            text = ' \n' + opening + ' ' + expression + ' ' + closing + '\n '
            q = self.question(latex_content=text)
            original = q.model_dump()
            with self.subTest(delimiters=(opening, closing)):
                self.module.validate_question_content(q, {4})
                self.assertEqual(q.latex_content, expression)
                self.assertEqual(q.model_dump(), dict(original, latex_content=expression))
                self.module.validate_question_content(q, {4})
                self.assertEqual(q.latex_content, expression)

    def test_bare_formulas_and_null_remain_unchanged(self):
        for text in (None, '', r'\sqrt{9}=3', r'\left(\frac{1}{2}\right)'):
            with self.subTest(text=text):
                q = self.question(latex_content=text)
                self.module.validate_question_content(q, {4})
                self.assertEqual(q.latex_content, text)

    def test_normalization_does_not_accept_broken_or_mixed_math(self):
        for text in ('$x', 'x$', '$$x$', r'\(x\]', '$x$ + $y$',
                     r'\(x\) and \(y\)', '$$', '$ $', '$$$$', r'\( \)', r'\[\]',
                     '$$$x$$$', r'$\frac{1}$', r'$\frac{}{2}$', r'$\unknown{x}$',
                     r'$\\frac{1}{2}$', r'$\$12$', r'$x_{2$', '$x^$', '$x&=2$'):
            with self.subTest(text=text):
                q = self.question(latex_content=text)
                with self.assertRaisesRegex(ValueError, 'latex_content'):
                    self.module.validate_question_content(q, {4})
                self.assertEqual(q.latex_content, text)

    def test_question_options_solution_and_hint_keep_inline_delimiters(self):
        q = self.question(latex_content=r'\[\frac{1}{2}\]',
            stem_text=r'Find $\frac{1}{2}+\frac{1}{2}$.',
            options_json={'A': '$0$', 'B': '$1$', 'C': '$2$', 'D': '$3$'},
            detailed_solution_latex=r'$\frac{1}{2}+\frac{1}{2}=1$. Choose B.',
            kid_friendly_hint=r'Add the numerators in $\frac{1+1}{2}$.')
        original = q.model_dump()
        self.module.validate_question_content(q, {4})
        self.assertEqual(q.model_dump(), dict(original, latex_content=r'\frac{1}{2}'))
        for field in ('stem_text', 'kid_friendly_hint', 'detailed_solution_latex'):
            with self.subTest(field=field):
                invalid = q.model_copy(update={field: r'$\frac{1}$'})
                with self.assertRaisesRegex(ValueError, field):
                    self.module.validate_question_content(invalid, {4})

    def test_proof_answer_latex_is_validated_in_generation_and_review(self):
        q = self.question(question_type='PROOF', options_json=None,
                          correct_answer=r'Therefore $x^{2}\geq 0$.')
        self.module.validate_question_content(q, {4})
        for answer in (r'Therefore $\frac{1}$.', r'Therefore \frac{1}{2}.', r'$$x=1$$'):
            with self.subTest(answer=answer), self.assertRaisesRegex(ValueError, 'correct_answer'):
                self.module.validate_question_content(q.model_copy(update={'correct_answer': answer}), {4})
        result = self.module.PracticeSetSchema(set_title='Test', total_questions=1, questions=[q])
        review = {'questions': [dict(position=1, topic_id=4, unambiguous=True,
            correct_answer=r'$\frac{1}$', detailed_solution_latex='A proof.') ]}
        with patch.object(self.module, 'request_structured_json', return_value=review):
            with self.assertRaisesRegex(ValueError, 'correct_answer'):
                self.module.review_practice_set(result, [{'id': 4}])
        self.assertEqual(result.questions[0].correct_answer, q.correct_answer)

    def test_all_question_fields_and_review_are_checked(self):
        from test_question_quality import QualityTests
        fixture = QualityTests()
        fixture.setUp()
        for field in ('stem_text', 'kid_friendly_hint', 'detailed_solution_latex', 'latex_content'):
            q = fixture.q.model_copy(update={field: r'\frac{1}'})
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                self.module.validate_question_content(q, {4})
        fixture.q.options_json['A'] = r'$\\frac{1}{2}$'
        with self.assertRaisesRegex(ValueError, 'options_json.A'):
            self.module.validate_question_content(fixture.q, {4})
        fixture.setUp()
        fixture.review['questions'][0]['detailed_solution_latex'] = r'$\frac{1}$'
        result = fixture.result()
        original = result.questions[0].detailed_solution_latex
        with patch.object(self.module, 'request_structured_json', return_value=fixture.review) as request:
            with self.assertRaisesRegex(ValueError, 'detailed_solution_latex'):
                self.module.review_practice_set(result, fixture.topics)
        self.assertIn(self.module.LATEX_FORMAT_RULES, request.call_args.args[0])
        self.assertEqual(result.questions[0].detailed_solution_latex, original)

    def test_solution_delimiter_repair_preserves_every_other_character(self):
        original = r'Divide: \frac{12}{2}=6. Then $6+2=8$. Choose B.'
        repaired = r'Divide: $\frac{12}{2}=6$. Then $6+2=8$. Choose B.'
        q = self.question(detailed_solution_latex=original)
        before = q.model_dump()
        with patch.object(self.module, 'request_structured_json', return_value={'text': repaired}) as request:
            self.module.validate_generated_question_content(q, {4})
        request.assert_called_once()
        self.assertEqual(request.call_args.args[3]['json_schema']['name'], 'latex_format')
        self.assertEqual(q.model_dump(), dict(before, detailed_solution_latex=repaired))
        self.module.validate_question_content(q, {4})

    def test_stem_delimiter_repair_preserves_content(self):
        original = r'Find \frac{1}{2} of $16$.'
        repaired = r'Find $\frac{1}{2}$ of $16$.'
        q = self.question(stem_text=original)
        before = q.model_dump()
        with patch.object(self.module, 'request_structured_json', return_value={'text': repaired}) as request:
            self.module.validate_generated_question_content(q, {4})
        request.assert_called_once()
        self.assertEqual(q.model_dump(), dict(before, stem_text=repaired))

    def test_stem_repair_rejects_rewrites_and_invalid_commands(self):
        for original, repaired in (
            (r'Find \frac{1}{2}.', r'Find $\frac{1}{3}$.'),
            (r'Find \unknown{x}.', r'Find $\unknown{x}$.'),
        ):
            q = self.question(stem_text=original)
            before = q.model_dump()
            with self.subTest(original=original), patch.object(self.module, 'request_structured_json',
                    return_value={'text': repaired}):
                with self.assertRaises(ValueError):
                    self.module.validate_generated_question_content(q, {4})
            self.assertEqual(q.model_dump(), before)

    def test_incomplete_stem_repair_retries_with_specific_feedback(self):
        original = r'Compare \frac{1}{2} and \frac{2}{3}.'
        partial = r'Compare $\frac{1}{2}$ and \frac{2}{3}.'
        repaired = r'Compare $\frac{1}{2}$ and $\frac{2}{3}$.'
        q = self.question(stem_text=original)
        before = q.model_dump()
        with patch.object(self.module, 'request_structured_json', side_effect=[
                {'text': partial}, {'text': repaired}]) as request:
            self.module.validate_generated_question_content(q, {4})
        self.assertEqual(request.call_count, 2)
        retry = json.loads(request.call_args.args[1])
        self.assertEqual(retry['text'], original)
        self.assertEqual(retry['previous_repair'], partial)
        self.assertEqual(retry['remaining_invalid_prose'], [r' and \frac{2}{3}.'])
        self.assertEqual(q.model_dump(), dict(before, stem_text=repaired))

    def test_incomplete_repair_is_bounded_and_logs_rejected_text(self):
        original = r'Compare \frac{1}{2} and \frac{2}{3}.'
        partial = r'Compare $\frac{1}{2}$ and \frac{2}{3}.'
        q = self.question(stem_text=original)
        before = q.model_dump()
        with patch.object(self.module, 'request_structured_json',
                return_value={'text': partial}) as request, patch('builtins.print') as output:
            with self.assertRaisesRegex(ValueError, 'stem_text: LaTeX outside math'):
                self.module.validate_generated_question_content(q, {4})
        self.assertEqual(request.call_count, 2)
        self.assertEqual(q.model_dump(), before)
        diagnostic = json.loads(output.call_args.args[0].removeprefix('LaTeX repair failed: '))
        self.assertEqual(diagnostic['original_text'], original)
        self.assertEqual(diagnostic['attempted_repair'], partial)

    def test_repair_rejects_rewritten_math_prose_and_existing_spans(self):
        original = r'Divide: \frac{12}{2}=6. Then $6+2=8$.'
        for repaired in (
            r'Divide: $\frac{12}{2}=7$. Then $6+2=8$.',
            r'Compute: $\frac{12}{2}=6$. Then $6+2=8$.',
            r'Divide: $\frac{12}{2}=6$. Then $6$+$2=8$.',
            r'Divide: $\frac{12}{2}=6$. Then 6+2=8.',
            original,
        ):
            q = self.question(detailed_solution_latex=original)
            before = q.model_dump()
            with self.subTest(repaired=repaired), patch.object(self.module, 'request_structured_json',
                    return_value={'text': repaired}):
                with self.assertRaises(ValueError):
                    self.module.validate_generated_question_content(q, {4})
            self.assertEqual(q.model_dump(), before)

    def test_repair_cannot_bypass_command_or_brace_validation(self):
        for original in (r'Divide: \frac{12}.', r'Use \unknown{x}.', r'Use x_{2.'):
            q = self.question(detailed_solution_latex=original)
            before = q.model_dump()
            prefix, formula = original.split(' ', 1)
            with self.subTest(original=original), patch.object(self.module, 'request_structured_json',
                    return_value={'text': prefix + ' $' + formula + '$'}) as request:
                with self.assertRaises(ValueError):
                    self.module.validate_generated_question_content(q, {4})
            request.assert_called_once()
            self.assertEqual(q.model_dump(), before)

    def test_valid_solutions_and_other_validation_errors_do_not_request_repairs(self):
        with patch.object(self.module, 'request_structured_json') as request:
            self.module.validate_generated_question_content(self.question(), {4})
            for updates in ({'detailed_solution_latex': r'$\frac{1}$'},
                            {'stem_text': r'Find $\frac{1}$.'}, {'correct_answer': 'Z'}):
                with self.subTest(updates=updates), self.assertRaises(ValueError):
                    self.module.validate_generated_question_content(self.question(**updates), {4})
        request.assert_not_called()

    def test_review_solution_gets_format_only_repair(self):
        q = self.question()
        result = self.module.PracticeSetSchema(set_title='Test', total_questions=1, questions=[q])
        original = r'Compute \frac{16}{2}=8. Choose B.'
        repaired = r'Compute $\frac{16}{2}=8$. Choose B.'
        review = {'questions': [dict(position=1, topic_id=4, unambiguous=True,
            correct_answer='B', detailed_solution_latex=original)]}
        with patch.object(self.module, 'request_structured_json', side_effect=[review, {'text': repaired}]) as request:
            self.module.review_practice_set(result, [{'id': 4}])
        self.assertEqual(request.call_count, 2)
        self.assertEqual(result.questions[0].detailed_solution_latex, repaired)
        self.assertEqual(result.questions[0].correct_answer, 'B')


if __name__ == '__main__':
    unittest.main()
