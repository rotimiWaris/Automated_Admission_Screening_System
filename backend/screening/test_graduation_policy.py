from datetime import date
from django.test import SimpleTestCase
from .graduation_policy import graduation_check

class GraduationPolicyTests(SimpleTestCase):
    def test_exact_allowance_boundaries_for_both_periods(self):
        for years in (1, 2):
            graduated = f'{2026-years}-12-19'
            self.assertEqual(graduation_check(graduated, years, date(2026,10,18))['status'], 'pending')
            self.assertEqual(graduation_check(graduated, years, date(2026,10,19))['status'], 'passed')
            self.assertEqual(graduation_check(graduated, years, date(2026,12,19))['status'], 'passed')

    def test_year_only_no_month_allowance(self):
        self.assertEqual(graduation_check('2025',1,date(2026,10,19))['status'],'passed')
        self.assertEqual(graduation_check('2025',2,date(2026,10,19))['status'],'pending')
        self.assertEqual(graduation_check('2024',2,date(2026,10,19))['status'],'passed')

    def test_invalid_missing_future_and_leap_day(self):
        self.assertEqual(graduation_check('',1)['status'],'failed')
        for value in ['invalid','2027','2027-01-01']:
            self.assertEqual(graduation_check(value,1,date(2026,10,19))['status'],'pending')
        self.assertEqual(graduation_check('2024-02-29',1,date(2024,12,28))['status'],'passed')
