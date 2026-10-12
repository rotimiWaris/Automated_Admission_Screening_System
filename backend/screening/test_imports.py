import csv
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from .table_import import import_students


ROOT = Path(__file__).resolve().parents[2]


from django.test import TestCase

class ImportTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_user(username='import-user'))

    def test_csv_and_excel_produce_identical_students_with_two_sittings(self):
        results = []
        for suffix in ['csv', 'xlsx']:
            path = ROOT / 'samples/synthetic-admissions/tabular' / f'screening-register.{suffix}'
            drafts, rows = import_students(path.read_bytes(), path.name)
            self.assertEqual(len(drafts), 20)
            self.assertEqual(len(drafts[2]['sittings']), 2)
            results.append([{k: d[k] for k in ['student_name', 'registration_number', 'course', 'jamb_score', 'sittings']} for d in drafts])
        self.assertEqual(results[0], results[1])

    @patch('screening.ocr_views._command', None)
    def test_table_upload_works_without_tesseract_and_returns_signed_drafts(self):
        path = ROOT / 'frontend/public/templates/admission-template.csv'
        response = self.client.post('/api/ocr/', {'file': SimpleUploadedFile(path.name, path.read_bytes()), 'page': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['source_format'], 'csv')
        self.assertIsNone(response.json()['confidence'])
        self.assertTrue(response.json()['token'])
        self.assertEqual(len(response.json()['table']['rows']), 1)

    def test_repeated_sitting_is_flagged_and_unknown_columns_rejected(self):
        path = ROOT / 'frontend/public/templates/admission-template.csv'
        raw = path.read_text(encoding='utf-8-sig')
        rows = list(csv.reader(StringIO(raw)))
        output = StringIO(); writer = csv.writer(output); writer.writerows([rows[0], rows[1], rows[1]])
        drafts, _ = import_students(output.getvalue().encode(), 'duplicate.csv')
        self.assertTrue(drafts[0]['duplicate_in_upload'])
        response = self.client.post('/api/ocr/', {'file': SimpleUploadedFile('bad.csv', b'unknown\nvalue\n')})
        self.assertEqual(response.status_code, 422)
