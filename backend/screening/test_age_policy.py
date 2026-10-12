from datetime import date
from django.test import SimpleTestCase
from .age_policy import apply_age_policy


class AgePolicyTests(SimpleTestCase):
    def assess(self, dob, route='ND Full-Time', today=date(2026, 1, 1), status='Eligible'):
        return apply_age_policy({'status':status,'checks':[]}, {'dob':dob}, today=today, admission_type=route)

    def test_nd_cutoff_boundaries_and_processing_year(self):
        for route in ['ND Full-Time','ND Part-Time']:
            self.assertEqual(self.assess('2010-09-30',route)['status'],'Eligible')
            self.assertEqual(self.assess('2010-10-01',route)['status'],'Pending Review')
            self.assertEqual(self.assess('2010-10-01',route,date(2027,1,1))['status'],'Eligible')
        self.assertEqual(self.assess('2010-09-30')['age_assessment']['age_at_cutoff'],16)
        self.assertEqual(self.assess('2010-09-30',today=date(2026,12,1))['age_assessment']['cutoff_date'],'2026-09-30')

    def test_missing_invalid_future_dob_requires_review(self):
        for dob in ['', 'invalid', '2027-01-01', '2010-02-30']:
            self.assertEqual(self.assess(dob)['status'],'Pending Review')
        self.assertEqual(self.assess('30/09/2010')['status'],'Eligible')
        self.assertEqual(self.assess('2000-01-01',status='Not Eligible')['status'],'Not Eligible')

    def test_hnd_has_no_age_check_even_without_dob(self):
        for route in ['HND Full-Time','HND Part-Time']:
            for dob in ['', '2015-01-01', 'invalid']:
                result=self.assess(dob,route)
                self.assertEqual(result,{'status':'Eligible','checks':[]})

    def test_supplied_age_does_not_replace_dob_or_approve_waiver(self):
        result=apply_age_policy({'status':'Eligible','checks':[]},{'age':20,'jamb_score':400},today=date(2026,1,1))
        self.assertEqual(result['status'],'Pending Review')
        self.assertIn('approved exceptional-candidate waiver',self.assess('2011-01-01')['checks'][0]['detail'])
