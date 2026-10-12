import copy
import json
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from .domain import EXAMINATIONS, evaluate
from .models import RuleSet, Verification

class ExaminationCatalogueTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username='catalogue-user'))

    def test_catalogue_and_screening_accept_all_listed_examinations(self):
        self.assertEqual(self.client.get('/api/catalogue/').json()['examinations'], EXAMINATIONS)
        rule = RuleSet(programme='Demo', minimum_credits=1, required_subjects=[{'subject': 'English Language', 'minimum_grade': 'C6'}])
        for exam in EXAMINATIONS:
            with self.subTest(exam=exam['label']):
                result = evaluate(rule, {'student_name': 'Demo', 'registration_number': 'DEMO', 'jamb_score': 250, 'confirmed': True, 'sittings': [dict(exam, year=2026, subjects=[{'subject': 'English Language', 'grade': 'B3'}])]})
                self.assertEqual(result['status'], 'Eligible')
                self.assertEqual(result['sittings'][0]['exam_type'], exam['exam_type'])

    def test_unlisted_or_mismatched_examinations_are_rejected(self):
        rule = RuleSet(programme='Demo')
        for board, exam_type in [('Other', 'School'), ('NBAIS', 'School'), ('NECO', 'WASC'), ('NABTEB', 'A-level'), ([], 'School')]:
            with self.subTest(board=board), self.assertRaisesRegex(ValueError, 'listed O’level'):
                evaluate(rule, {'student_name': 'Demo', 'registration_number': 'DEMO', 'jamb_score': 250, 'confirmed': True, 'sittings': [{'board': board, 'exam_type': exam_type}]})


class ScreeningTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_user(username='authenticated-fixture'))
        self.rule = RuleSet.objects.create(programme='Computing demo', academic_session='Demo', minimum_jamb=180, minimum_credits=5, required_subjects=[{'subject': s, 'minimum_grade': 'C6'} for s in ['English Language', 'Mathematics', 'Physics']])
        self.data = {'rule_id': self.rule.id, 'rule_revision': 1, 'student_name': 'Demo Student', 'registration_number': 'DEMO-001', 'jamb_score': 180, 'confirmed': True, 'save': False, 'sittings': [{'board': 'WAEC', 'exam_type': 'School', 'year': 2025, 'subjects': [{'subject': s, 'grade': 'C6'} for s in ['English Language', 'Mathematics', 'Physics', 'Chemistry', 'Biology']]}]}
        self.staff = get_user_model().objects.create_user(username='staff', password='test-password-123', is_staff=True)
        self.other = get_user_model().objects.create_user(username='other', password='test-password-123')

    def post(self, data=None):
        return self.client.post('/api/screen/', json.dumps(data if data is not None else self.data), content_type='application/json')

    def test_boundary_score_and_c6_pass(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'Eligible')
        self.assertFalse(Verification.objects.exists())

    def test_low_jamb_explained(self):
        self.data['jamb_score'] = 179
        result = self.post().json()
        self.assertEqual(result['status'], 'Not Eligible')
        self.assertEqual(result['checks'][0]['status'], 'failed')

    def test_missing_subject_and_insufficient_credits(self):
        self.data['sittings'][0]['subjects'].pop(0)
        result = self.post().json()
        self.assertEqual(result['status'], 'Not Eligible')
        self.assertTrue(any('Missing subject' in c['detail'] for c in result['checks']))
        self.assertEqual(next(c for c in result['checks'] if c['label'] == 'O’level credits')['status'], 'failed')

    def test_low_required_grade(self):
        self.rule.required_subjects[0]['minimum_grade'] = 'B3'
        self.rule.save()
        self.assertEqual(self.post().json()['status'], 'Not Eligible')

    def test_unconfirmed_missing_subject_is_pending(self):
        self.data['confirmed'] = False
        self.data['sittings'][0]['subjects'].pop(0)
        self.assertEqual(self.post().json()['status'], 'Pending Review')

    def test_awaiting_or_missing_jamb_remains_pending(self):
        for score, grade in [(None, 'C6'), (120, 'Awaiting'), (250, 'Withheld'), (250, 'Unreadable')]:
            with self.subTest(score=score, grade=grade):
                self.data['jamb_score'] = score
                self.data['sittings'][0]['subjects'][0]['grade'] = grade
                self.assertEqual(self.post().json()['status'], 'Pending Review')

    def test_duplicate_subject_rejected(self):
        self.data['sittings'][0]['subjects'].append({'subject': 'Mathematics', 'grade': 'A1'})
        self.assertEqual(self.post().status_code, 400)

    def test_invalid_scores_rejected(self):
        for score in [-1, 401, 180.2, True, '180']:
            with self.subTest(score=score):
                self.data['jamb_score'] = score
                self.assertEqual(self.post().status_code, 400)

    def test_combining_uses_best_grade_counts_distinct_subjects(self):
        self.data['sittings'][0]['subjects'][0]['grade'] = 'F9'
        self.data['sittings'].append({'board': 'NECO', 'exam_type': 'Private/GCE', 'year': 2026, 'subjects': [{'subject': 'English Language', 'grade': 'B3'}, {'subject': 'Mathematics', 'grade': 'A1'}]})
        result = self.post().json()
        self.assertEqual(result['status'], 'Eligible')
        self.assertIn('5 distinct', next(c for c in result['checks'] if c['label'] == 'O’level credits')['detail'])

    def test_forbidden_combining_is_not_performed(self):
        self.rule.allow_combining = False
        self.rule.save()
        self.data['sittings'].append(copy.deepcopy(self.data['sittings'][0]))
        result = self.post().json()
        self.assertEqual(result['status'], 'Not Eligible')
        self.assertFalse(any(c['label'] == 'O’level credits' for c in result['checks']))

    def test_maximum_sittings_enforced(self):
        self.rule.max_sittings = 1
        self.rule.allow_combining = False
        self.rule.save()
        self.data['sittings'].append(copy.deepcopy(self.data['sittings'][0]))
        self.assertEqual(self.post().json()['checks'][1]['status'], 'failed')

    def test_malformed_requests(self):
        for payload in [[], None, {'sittings': 'bad'}, self.data | {'sittings': [None]}, self.data | {'sittings': []}]:
            with self.subTest(payload=payload):
                response = self.client.post('/api/screen/', json.dumps(payload), content_type='application/json')
                self.assertEqual(response.status_code, 400)

    def test_save_requires_login(self):
        self.client.logout()
        self.data['save'] = True
        self.assertEqual(self.post().status_code, 401)
        self.assertEqual(self.client.get('/api/history/').status_code, 401)

    def test_history_is_private_and_snapshot_survives_edits(self):
        self.client.force_login(self.staff)
        self.data['save'] = True
        self.assertEqual(self.post().status_code, 200)
        self.rule.minimum_jamb = 300
        self.rule.save()
        history = self.client.get('/api/history/').json()['history']
        self.assertEqual(history[0]['rules']['minimum_jamb'], 180)
        self.assertEqual(history[0]['status'], 'Eligible')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get('/api/history/').json()['history'], [])

    def test_staff_can_edit_and_stale_updates_rejected(self):
        payload = self.rule.snapshot() | {'minimum_jamb': 220}
        url = f'/api/rules/{self.rule.id}/'
        self.assertEqual(self.client.put(url, json.dumps(payload), content_type='application/json').status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.put(url, json.dumps(payload), content_type='application/json').status_code, 403)
        self.client.force_login(self.staff)
        response = self.client.put(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.json()['revision'], 2)
        self.assertEqual(response.json()['minimum_jamb'], 220)
        self.assertEqual(self.client.put(url, json.dumps(payload), content_type='application/json').status_code, 409)
        self.assertEqual(self.post().status_code, 409)

    def test_invalid_rule_cannot_be_created(self):
        self.client.force_login(self.staff)
        for changes in [{'minimum_jamb': 401}, {'minimum_credits': 0}, {'required_subjects': []}, {'max_sittings': 1, 'allow_combining': True}]:
            with self.subTest(changes=changes):
                response = self.client.post('/api/rules/', json.dumps(self.rule.snapshot() | changes), content_type='application/json')
                self.assertEqual(response.status_code, 400)

    def test_inactive_rules_cannot_be_used(self):
        self.rule.active = False
        self.rule.save()
        self.assertEqual(self.client.get('/api/rules/').json()['rules'], [])
        self.assertEqual(self.post().status_code, 404)

    def test_csrf_and_login_logout(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/screen/', json.dumps(self.data), content_type='application/json').status_code, 401)
        token = client.get('/api/session/').json()['csrf']
        response = client.post('/api/login/', json.dumps({'username': 'staff', 'password': 'test-password-123'}), content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['user']['is_staff'])
        token = response.json()['csrf']
        self.assertEqual(client.post('/api/screen/', json.dumps(self.data), content_type='application/json', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.post('/api/logout/', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertIsNone(client.get('/api/session/').json()['user'])
