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
