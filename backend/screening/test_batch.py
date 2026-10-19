import json
from copy import deepcopy
from django.core import signing
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import RuleSet, Verification


class BatchTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_user(username='authenticated-fixture'))
        self.rule = RuleSet.objects.create(programme='Computer Science', academic_session='2026/2027', required_subjects=[{'subject': 'English Language', 'minimum_grade': 'C6'}])
        self.draft = {'student_name': 'Synthetic Student', 'registration_number': 'TEST-001', 'course': 'Computer Science', 'jamb_score': 240,
                      'confidence': 95, 'review_issues': [], 'sittings': [{'board': 'WAEC', 'exam_type': 'School', 'year': 2025,
                      'subjects': [{'subject': s, 'grade': 'B3'} for s in ['English Language', 'Mathematics', 'Physics', 'Chemistry', 'Biology']]}]}

    def token(self, drafts, page=1, document='one'):
        return signing.dumps({'document': document, 'page': page, 'drafts': drafts}, salt='ocr-batch')

    def post(self, drafts=None, **overrides):
        payload = {'pages': [self.token(drafts or [self.draft])], 'save': False,
                   'course_rules': {'Computer Science': {'id': self.rule.id, 'revision': self.rule.revision}}} | overrides
        return self.client.post('/api/screen-batch/', json.dumps(payload), content_type='application/json')

    def test_multiple_students_screen_without_retyping(self):
        second = deepcopy(self.draft)
        second.update(registration_number='TEST-002', jamb_score=100)
        response = self.post([self.draft, second])
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r['status'] for r in response.json()['results']], ['Eligible', 'Not Eligible'])
        self.assertFalse(Verification.objects.exists())

    def test_uncertainty_and_missing_course_stay_pending(self):
        self.draft['review_issues'] = ['Uncertain grade']
        self.assertEqual(self.post().json()['results'][0]['status'], 'Pending Review')
        self.draft['course'] = 'Unknown department'
        result = self.post(course_rules={}).json()['results'][0]
        self.assertEqual(result['status'], 'Pending Review')
        self.assertIsNone(result['result'])

    def test_duplicate_registrations_are_not_merged(self):
        result = self.post([self.draft, self.draft]).json()
        self.assertEqual(len(result['results']), 2)
        self.assertEqual(result['summary'], {'Eligible': 2})

    def test_invalid_fields_do_not_abort_other_students(self):
        missing = deepcopy(self.draft)
        missing.update(registration_number='', student_name='Missing registration')
        results = self.post([self.draft, missing]).json()['results']
        self.assertEqual([r['status'] for r in results], ['Eligible', 'Pending Review'])

    def test_signature_duplicate_pages_and_mixed_documents_rejected(self):
        self.assertEqual(self.post(pages=['modified-token']).status_code, 400)
        one = self.token([self.draft])
        self.assertEqual(self.post(pages=[one, one]).status_code, 400)
        self.assertEqual(self.post(pages=[one, self.token([self.draft], 2, 'two')]).status_code, 400)

    def test_stale_revision_cannot_save_partial_batch(self):
        self.assertEqual(self.post(course_rules={'Computer Science': {'id': self.rule.id, 'revision': 0}}).status_code, 409)
        self.assertFalse(Verification.objects.exists())

    def test_saved_history_requires_login_and_includes_provenance(self):
        self.client.logout()
        self.assertEqual(self.post(save=True).status_code, 401)
        user = get_user_model().objects.create_user(username='batch-user')
        self.client.force_login(user)
        response = self.post(save=True)
        self.assertEqual(response.status_code, 200)
        saved = Verification.objects.get(owner=user)
        self.assertEqual(saved.result['ocr']['confidence'], 95)
        self.assertEqual(saved.result['rules']['revision'], self.rule.revision)

    def test_unstructured_input_never_creates_workbook(self):
        from unittest.mock import patch
        with patch('screening.batch_views.workbook_bytes') as export:
            response=self.post()
        self.assertEqual(response.status_code,200)
        self.assertNotIn('excel',response.json())
        self.assertIn('expected admission register columns',response.json()['export_notice'])
        export.assert_not_called()
