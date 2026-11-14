import importlib
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


if __name__ == '__main__':
    unittest.main()
