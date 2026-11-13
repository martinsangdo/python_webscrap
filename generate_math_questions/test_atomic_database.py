"""Opt-in real PostgreSQL tests; use a NEW disposable practice_atomic_test* database.

ATOMIC_TEST_DATABASE_URL=postgresql://localhost:55439/practice_atomic_test \
    python3 -m unittest test_atomic_database -v
"""
import json
import os
from pathlib import Path
import subprocess
import unittest
from urllib.parse import urlparse

ROOT = Path(__file__).parent
DATABASE_URL = os.getenv('ATOMIC_TEST_DATABASE_URL')


@unittest.skipUnless(DATABASE_URL, 'requires a disposable PostgreSQL database')
class AtomicDatabaseTests(unittest.TestCase):
    @classmethod
    def sql(cls, sql, check=True):
        return subprocess.run(['psql', DATABASE_URL, '-X', '-qAt', '-v', 'ON_ERROR_STOP=1'],
                              input=sql, text=True, capture_output=True, check=check)

    @classmethod
    def setUpClass(cls):
        if not urlparse(DATABASE_URL).path.startswith('/practice_atomic_test'):
            raise ValueError('Integration tests require a disposable practice_atomic_test* database')
        # The schema must be empty: fixture creation intentionally fails otherwise.
        cls.sql((ROOT / 'tests/atomic_schema.sql').read_text())
        cls.sql("""DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN CREATE ROLE anon; END IF;
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN CREATE ROLE authenticated; END IF;
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN CREATE ROLE service_role; END IF;
        END $$;""")
        cls.sql((ROOT / 'migrations/20261113_atomic_practice_sets.sql').read_text())
        cls.sql("""
          INSERT INTO certifications (id, full_name, default_time_minutes, default_question_type, prompt_philosophy)
          VALUES ('TEST', 'Test', 60, 'INTEGER_FILL', 'Math');
          INSERT INTO exam_levels (id, certification_id, level_code, target_grade_min, target_grade_max, total_questions, max_score)
          VALUES (1, 'TEST', 'LEVEL', 3, 4, 2, 4);
          INSERT INTO topics (id, domain_code, title) VALUES (1, 'MATH', 'Math');
          INSERT INTO exam_structure_rules (level_id, section_name, question_type, questions_count, points_per_correct, penalty_points, chart_questions_count, chart_types)
          VALUES (1, 'A', 'INTEGER_FILL', 2, 2, 0, 1, ARRAY['BAR']);
        """)

    def setUp(self):
        self.sql('TRUNCATE exam_set_questions, questions, exam_sets;')
        self.sql('DROP TRIGGER IF EXISTS fail_publish ON exam_sets;')
        self.payload = dict(certification_id='TEST', level_id=1, title='Atomic test', description='Test', time_minutes=60)
        q = dict(position=1, certification_id='TEST', level_id=1, topic_id=1, question_type='INTEGER_FILL',
                 stem_text='Add', correct_answer='5', points=2, penalty_points=0, difficulty_rating=1,
                 detailed_solution_latex='2+3=5', kid_friendly_hint='Add',
                 chart_type='BAR', chart_data={'categories': ['A'], 'values': [5]}, image_url='https://example.com/1.svg')
        self.questions = [q, dict(q, position=2, chart_type=None, chart_data=None, image_url=None)]

    def statement(self):
        def literal(value):
            return "'" + json.dumps(value).replace("'", "''") + "'::jsonb"
        return f'SELECT public.save_complete_practice_set({literal(self.payload)}, {literal(self.questions)});'

    def counts(self):
        return self.sql('SELECT (SELECT count(*) FROM exam_sets), (SELECT count(*) FROM questions), (SELECT count(*) FROM exam_set_questions);').stdout.strip()

    def test_complete_commit_and_duplicate_rejected(self):
        result = json.loads(self.sql(self.statement()).stdout)
        self.assertEqual(result['question_count'], 2)
        self.assertEqual(self.counts(), '1|2|2')
        self.assertEqual(self.sql('SELECT is_published FROM exam_sets;').stdout.strip(), 't')
        self.assertNotEqual(self.sql(self.statement(), check=False).returncode, 0)
        self.assertEqual(self.counts(), '1|2|2')

    def test_second_question_foreign_key_failure_rolls_back_first_question_and_set(self):
        self.questions[1]['topic_id'] = 999
        result = self.sql(self.statement(), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('foreign key', result.stderr)
        self.assertEqual(self.counts(), '0|0|0')

    def test_missing_question_position_or_image_rejected(self):
        originals = json.loads(json.dumps(self.questions))
        for problem in ('count', 'position', 'image'):
            self.questions = json.loads(json.dumps(originals))
            if problem == 'count': self.questions.pop()
            if problem == 'position': self.questions[1]['position'] = 1
            if problem == 'image': self.questions[0]['image_url'] = None
            with self.subTest(problem=problem):
                self.assertNotEqual(self.sql(self.statement(), check=False).returncode, 0)
                self.assertEqual(self.counts(), '0|0|0')

    def test_failure_at_publish_rolls_back_all_rows(self):
        self.sql("""CREATE OR REPLACE FUNCTION test_fail_publish() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'injected publish failure'; END $$;
            CREATE TRIGGER fail_publish BEFORE UPDATE ON exam_sets FOR EACH ROW EXECUTE FUNCTION test_fail_publish();""")
        result = self.sql(self.statement(), check=False)
        self.assertIn('injected publish failure', result.stderr)
        self.assertEqual(self.counts(), '0|0|0')

    def test_backend_termination_before_commit_rolls_back_all_rows(self):
        self.sql("""CREATE OR REPLACE FUNCTION test_fail_publish() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN PERFORM pg_terminate_backend(pg_backend_pid()); RETURN NEW; END $$;
            CREATE TRIGGER fail_publish BEFORE UPDATE ON exam_sets FOR EACH ROW EXECUTE FUNCTION test_fail_publish();""")
        result = self.sql(self.statement(), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('terminating connection', result.stderr)
        self.assertEqual(self.counts(), '0|0|0')

    def test_only_service_role_has_execute_permission(self):
        result = self.sql("""SELECT
            has_function_privilege('anon', 'public.save_complete_practice_set(jsonb,jsonb)', 'EXECUTE'),
            has_function_privilege('authenticated', 'public.save_complete_practice_set(jsonb,jsonb)', 'EXECUTE'),
            has_function_privilege('service_role', 'public.save_complete_practice_set(jsonb,jsonb)', 'EXECUTE');""")
        self.assertEqual(result.stdout.strip(), 'f|f|t')

    def test_concurrent_saves_commit_only_one_set(self):
        processes = [subprocess.Popen(
            ['psql', DATABASE_URL, '-X', '-qAt', '-v', 'ON_ERROR_STOP=1'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ) for _ in range(2)]
        for process in processes:
            process.stdin.write(self.statement())
            process.stdin.close()
            process.stdin = None
        results = [process.communicate(timeout=10) for process in processes]
        self.assertEqual(sum(process.returncode == 0 for process in processes), 1)
        self.assertTrue(any('already exists' in stderr for _, stderr in results))
        self.assertEqual(self.counts(), '1|2|2')
