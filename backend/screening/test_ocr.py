from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, Client
from PIL import Image
from result_ocr import OCRError
from .result_parser import subject_rows, sitting, score, parse_drafts

class ParserTests(SimpleTestCase):
    def test_compact_subject_labels_and_unknown_grade_preserve_subject(self):
        self.assertEqual(subject_rows('Mathematics:C6\nPhysics:CS'), [
            {'subject': 'Mathematics', 'grade': 'C6'}, {'subject': 'Physics', 'grade': 'Unreadable'}])

    def test_grade_matching_does_not_guess_ambiguous_grades(self):
        self.assertEqual(subject_rows('English Language B3\nMathematics C6\nPhysics Cb\nBiology Withheld'), [
            {'subject': 'English Language', 'grade': 'B3'}, {'subject': 'Mathematics', 'grade': 'C6'}, {'subject': 'Physics', 'grade': 'Unreadable'}, {'subject': 'Biology', 'grade': 'Withheld'}])

    def test_missing_board_type_year_are_not_invented(self):
        self.assertEqual(sitting('Mathematics C6'), {'board': '', 'exam_type': '', 'year': '', 'subjects': [{'subject': 'Mathematics', 'grade': 'C6'}]})
        self.assertEqual(sitting('NECO SSCE External 2025')['exam_type'], 'Private/GCE')

    def test_score_needs_a_label_or_denominator(self):
        self.assertIsNone(score('Registration 245'))
        self.assertIsNone(score('JAMB score: 450'))
        self.assertEqual(score('JAMB total score: 245'), 245)

    def test_unknown_multi_student_layout_is_not_merged(self):
        words = [{'text': word, 'top': i * 30, 'height': 20, 'left': 0, 'width': 250} for i, word in enumerate(['DEMO-UTME-0001', 'Mathematics C6', 'DEMO-UTME-0002', 'English Language B3'])]
        drafts, warnings = parse_drafts({'words': words, 'width': 600, 'height': 800})
        self.assertEqual(drafts, [])
        self.assertIn('Multiple students', warnings[0])

from django.test import TestCase

class OCRAPITests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_user(username='ocr-user'))

    def upload(self, data=b'invalid', page='1'):
        return {'file': SimpleUploadedFile('result.png', data, content_type='image/png'), 'page': page}

    @patch('screening.ocr_views._command', None)
    def test_missing_engine_has_actionable_response(self):
        response = self.client.post('/api/ocr/', self.upload())
        self.assertEqual(response.status_code, 503)
        self.assertIn('Tesseract', response.json()['error'])

    @patch('screening.ocr_views._command', 'tesseract')
    def test_invalid_file_page_and_missing_upload(self):
        self.assertEqual(self.client.post('/api/ocr/', {}).status_code, 400)
        self.assertEqual(self.client.post('/api/ocr/', self.upload(page='abc')).status_code, 400)
        self.assertEqual(self.client.post('/api/ocr/', self.upload()).status_code, 422)

    @patch('screening.ocr_views._command', 'tesseract')
    @patch('screening.ocr_views.extract_page')
    def test_oversized_upload_rejected_before_ocr(self, extract):
        self.assertEqual(self.client.post('/api/ocr/', self.upload(b'x' * (10 * 1024 * 1024 + 1))).status_code, 413)
        extract.assert_not_called()

    @patch('screening.ocr_views._command', 'tesseract')
    def test_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        from django.contrib.auth import get_user_model
        client.force_login(get_user_model().objects.get(username='ocr-user'))
        self.assertEqual(client.post('/api/ocr/', self.upload()).status_code, 403)

    @patch('screening.ocr_views._command', 'tesseract')
    @patch('screening.ocr_views.extract_page', side_effect=OCRError('OCR timed out'))
    def test_failure_releases_capacity(self, extract):
        for _ in range(2):
            self.assertEqual(self.client.post('/api/ocr/', self.upload()).status_code, 422)

    @patch('screening.ocr_views._command', 'tesseract')
    @patch('screening.ocr_views.extract_page')
    def test_success_returns_page_text_and_preview(self, extract):
        data = {'text': 'Unrecognised layout', 'words': [], 'width': 200, 'height': 200, 'warnings': []}
        extract.return_value = SimpleNamespace(page_number=2, page_count=5, preview_png=b'png', result=SimpleNamespace(to_dict=lambda: data))
        response = self.client.post('/api/ocr/', self.upload(page='2'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['page'], 2)
        self.assertEqual(response.json()['page_count'], 5)
        self.assertEqual(response.json()['drafts'], [])
