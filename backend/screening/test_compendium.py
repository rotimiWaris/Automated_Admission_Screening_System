import copy
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, SimpleTestCase
from .compendium import from_source, NAMES
from .criteria import matches
from .domain import evaluate, validate_rules
from .models import RuleSet, Verification


SOURCE = Path(settings.BASE_DIR).parent / 'compendium.txt'


class CompendiumTests(SimpleTestCase):
    def rule(self, row):
        entry = copy.deepcopy(from_source(SOURCE.read_text(encoding='utf-8-sig'))[row - 1])
        return RuleSet(programme=entry['programme'], minimum_jamb=100, criteria=entry,
                       required_subjects=[{'subject': NAMES[s], 'minimum_grade': 'C6'} for s in ['E','M']])

    def data(self, credits, utme, passes=''):
        subjects = [{'subject': NAMES[s], 'grade': 'C6'} for s in credits.split(',')]
        subjects += [{'subject': NAMES[s], 'grade': 'E8'} for s in passes.split(',') if s]
        return {'student_name': 'Test Applicant', 'registration_number': 'TEST-001',
                'confirmed': True, 'jamb_score': 100,
                'jamb_subjects': [NAMES[s] for s in utme.split(',')],
                'sittings': [{'board':'WAEC', 'exam_type':'School', 'year':2026, 'subjects':subjects}]}

    def test_independent_examples_for_all_28_programmes(self):
        cases = [
            ('E,M,Ec,Co,Ac','E,M,Ec,Co',''), ('E,M,Ec,St,Mk','E,M,Ec,Gov',''),
            ('E,M,Co,Mk,Gov','E,M,Co,Ac',''), ('E,M,Ec,Co,Ac','E,M,H,Ac',''),
            ('E,M,L,Gov,H','E,L,Gov,H',''), ('E,M,Ty,Sh,OP','E,M,Ec,Gov',''),
            ('E,M,Ec,BM,Ac','E,Gov,Ec,Co',''), ('E,M,H,Mu,F','E,H,Mu,F',''),
            ('E,M,P,C,Ec','E,M,B,P','B'), ('E,M,C,B,Ec','E,B,Ec,C','P'),
            ('E,M,B,P,C','E,B,P,C',''), ('E,M,G,Ec,H','E,M,C,P',''),
            ('E,M,P,C,B','E,C,B,A',''), ('E,M,C,B,Ec','E,M,C,B','P'),
            ('E,M,P,C,B','E,M,P,C',''), ('E,M,Ec,G,St','E,Ec,H,M',''),
            ('E,M,P,C,B','E,C,B,P',''), ('E,M,FA,C,H','E,FA,M,H',''),
            ('E,M,P,C,G','E,M,P,C',''), ('E,M,P,C,B','E,M,P,C',''),
            ('E,M,Ec,P,C','E,M,Ec,P',''), ('E,M,P,C,G','E,P,M,G',''),
            ('E,M,P,C,G','E,C,Ec,M',''), ('E,M,P,C,B','E,G,P,C',''),
            ('E,M,P,C,TD','E,M,P,C',''), ('E,M,P,C,CS','E,M,P,C',''),
            ('E,M,P,C,AM','E,M,P,C',''), ('E,M,P,C,BC','E,M,P,C',''),
        ]
        self.assertEqual(len(cases), 28)
        for row, args in enumerate(cases, 1):
            with self.subTest(row=row):
                result = evaluate(self.rule(row), self.data(*args))
                self.assertFalse([c for c in result['checks'] if c['status']=='failed'])
                self.assertEqual(result['status'], 'Eligible')

    def test_urban_geography_compulsory_and_maths_olevel_only(self):
        data=self.data('E,M,P,C,B','E,G,Gov,TD')
        self.assertEqual(evaluate(self.rule(24),data)['status'],'Eligible')
        data['jamb_subjects'][1]=NAMES['M']
        self.assertEqual(evaluate(self.rule(24),data)['status'],'Not Eligible')
        data['jamb_subjects']=[NAMES[s] for s in ['E','G','P','C']]
        data['sittings'][0]['subjects'][1]['grade']='F9'
        self.assertEqual(evaluate(self.rule(24),data)['status'],'Not Eligible')

    def test_owner_categories_and_slt_correction(self):
        for row in [5,8]:
            data=self.data('E,M,L,Gov,H','E,B,CS,Ec')
            self.assertEqual(evaluate(self.rule(row),data)['status'],'Eligible')
            data['jamb_subjects'][-1]=NAMES['Mk']
            self.assertEqual(evaluate(self.rule(row),data)['status'],'Not Eligible')
        for alternative in ['B','A']:
            data=self.data('E,M,P,C,Ec','E,M,P,'+alternative,'B')
            self.assertEqual(evaluate(self.rule(9),data)['status'],'Eligible')
            data['jamb_subjects'][2]=NAMES['C']
            self.assertEqual(evaluate(self.rule(9),data)['status'],'Not Eligible')

    def test_unrelated_credits_do_not_satisfy_engineering(self):
        result = evaluate(self.rule(28), self.data('E,M,P,C,F','E,M,P,C'))
        self.assertEqual(result['status'], 'Not Eligible')

    def test_physics_pass_food_and_pharmacy(self):
        for row in [10,14]:
            data = self.data('E,M,C,B,Ec','E,M,C,B','P')
            self.assertEqual(evaluate(self.rule(row),data)['status'],'Eligible')
            data['sittings'][0]['subjects'][-1]['grade']='F9'
            self.assertEqual(evaluate(self.rule(row),data)['status'],'Not Eligible')

    def test_mass_communication_literature_is_pass_not_credit(self):
        data = self.data('E,M,Gov,H,FA','E,Gov,H,L','L')
        result = evaluate(self.rule(5),data)
        self.assertEqual(next(c['status'] for c in result['checks'] if c['label'].startswith('Additional pass')), 'passed')
        data['sittings'][0]['subjects'][-1]['grade']='F9'
        result = evaluate(self.rule(5),data)
        self.assertEqual(next(c['status'] for c in result['checks'] if c['label'].startswith('Additional pass')), 'failed')

    def test_slt_requires_third_science_pass_and_two_distinct_science_groups(self):
        data = self.data('E,M,P,C,Ec','E,M,B,P','B')
        self.assertFalse(any(c['status']=='failed' for c in evaluate(self.rule(9),data)['checks']))
        data['sittings'][0]['subjects'][-1]['grade']='F9'
        self.assertTrue(any(c['status']=='failed' for c in evaluate(self.rule(9),data)['checks']))
        result = evaluate(self.rule(9), self.data('E,M,B,A,Ec','E,M,B,P','P,C'))
        self.assertEqual(next(c['status'] for c in result['checks'] if c['label']=='Programme credit combination'),'failed')

    def test_sbms_separate_economics_commerce_accounting(self):
        for row in [1,2,3,4]:
            self.assertEqual(evaluate(self.rule(row),self.data('E,M,Ec,Co,Ac','E,M,Ec,Co'))['status'],'Eligible')

    def test_subject_cannot_fill_two_credit_slots(self):
        result = evaluate(self.rule(11),self.data('E,M,FN,P,Y','E,B,P,C'))
        self.assertEqual(result['status'],'Eligible')
        result = evaluate(self.rule(11),self.data('E,M,FN,P,Ac','E,B,P,C'))
        self.assertEqual(result['status'],'Not Eligible')

    def test_estate_science_alternative_and_urban_separate_sciences(self):
        self.assertEqual(evaluate(self.rule(21),self.data('E,M,Ec,P,C','E,M,Ec,P'))['status'],'Eligible')
        result = evaluate(self.rule(24),self.data('E,M,P,C,B','E,G,P,C'))
        self.assertEqual(next(c['status'] for c in result['checks'] if c['label']=='Programme credit combination'),'passed')

    def test_architecture_advantage_is_not_mandatory(self):
        self.assertEqual(evaluate(self.rule(19),self.data('E,M,P,C,G','E,M,P,C'))['status'],'Eligible')

    def test_utme_wrong_missing_duplicate_and_boundary(self):
        rule = self.rule(26)
        data = self.data('E,M,P,C,CS','E,M,P,C')
        data['jamb_score']=99
        self.assertEqual(evaluate(rule,data)['status'],'Not Eligible')
        data['jamb_score']=100
        data['jamb_subjects'][-1]=NAMES['Ec']
        self.assertEqual(evaluate(rule,data)['status'],'Not Eligible')
        data.pop('jamb_subjects')
        self.assertEqual(evaluate(rule,data)['status'],'Pending Review')
        data['jamb_subjects']=[NAMES['E']]*4
        with self.assertRaises(ValueError): evaluate(rule,data)

    def test_two_sittings_best_grade_and_unknown_grade(self):
        data=self.data('E,M,P,C,CS','E,M,P,C')
        data['sittings'][0]['subjects'][0]['grade']='F9'
        data['sittings'].append({'board':'NECO','exam_type':'School','year':2026,'subjects':[{'subject':NAMES['E'],'grade':'C6'}]})
        self.assertEqual(evaluate(self.rule(26),data)['status'],'Eligible')
        data['sittings'][1]['subjects'][0]['grade']='Unreadable'
        self.assertEqual(evaluate(self.rule(26),data)['status'],'Pending Review')

    def test_electrical_engineering_accepts_two_sittings_without_clarification(self):
        data=self.data('E,M,P,C,TD','E,M,P,C')
        last=data['sittings'][0]['subjects'].pop()
        data['sittings'].append({'board':'NECO','exam_type':'School','year':2026,'subjects':[last]})
        result=evaluate(self.rule(25),data)
        self.assertEqual(result['status'],'Eligible')
        self.assertFalse(any(c['label']=='Compendium clarification required' for c in result['checks']))

    def test_validation_rejects_bad_criteria_and_other_track(self):
        rule=self.rule(26)
        values=rule.snapshot()
        validate_rules(values)
        values['admission_type']='HND Full-Time'
        with self.assertRaises(ValueError): validate_rules(values)
        values['admission_type']='ND Full-Time'
        values['criteria']['credit_paths'][0][0]['count']=100
        with self.assertRaises(ValueError): validate_rules(values)


class CompendiumInstallTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_user(username='authenticated-fixture'))

    def test_batch_import_checks_utme_subjects_with_compendium(self):
        import csv
        from io import StringIO
        from django.core import signing
        from .table_import import import_students
        call_command('load_compendium', verbosity=0)
        rule=RuleSet.objects.get(programme='Computer Engineering')
        stream=StringIO()
        writer=csv.writer(stream)
        writer.writerow(['student_name','registration_number','course','jamb_score','jamb_subjects','sitting','board','exam_type','year','English Language','Mathematics','Physics','Chemistry','Computer Studies'])
        writer.writerow(['Applicant','TEST100','Computer Engineering',100,'Use of English; Mathematics; Physics; Chemistry',1,'WAEC','School',2026,'C6','C6','C6','C6','C6'])
        drafts,_=import_students(stream.getvalue().encode(),'test.csv')
        token=signing.dumps({'document':'test','page':1,'drafts':drafts},salt='ocr-batch')
        response=self.client.post('/api/screen-batch/',{'pages':[token],'save':False,'course_rules':{'Computer Engineering':{'id':rule.id,'revision':rule.revision}}},content_type='application/json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['summary'],{'Eligible':1})

    def test_single_student_labelled_utme_aliases_do_not_use_olevel(self):
        from .jamb_subjects import labelled_subjects
        self.assertEqual(labelled_subjects('UTME subjects: Use of English; Maths; Principles of Accounts; Commerce'),
                         ['English Language','Mathematics','Financial Accounting','Commerce'])
        self.assertEqual(labelled_subjects('English Language C6\nMathematics C6\nPhysics C6\nChemistry C6'),[])
        with self.assertRaises(ValueError): labelled_subjects('JAMB subjects: English, Maths, Physics, Maths')

    def test_install_archives_demo_preserves_history_and_is_idempotent(self):
        rule=RuleSet.objects.create(programme='Computing',academic_session='2026/2027')
        from django.contrib.auth import get_user_model
        user=get_user_model().objects.create_user(username='owner')
        old={'student':{'registration_number':'OLD'},'rules':rule.snapshot()}
        record=Verification.objects.create(owner=user,result=old)
        call_command('load_compendium',verbosity=0)
        rule.refresh_from_db()
        self.assertFalse(rule.active)
        self.assertEqual(RuleSet.objects.filter(active=True).count(),28)
        for installed in RuleSet.objects.filter(active=True):
            validate_rules(installed.snapshot())
            self.assertEqual(installed.admission_type,'All Admission Type')
            self.assertEqual(installed.academic_session,'All sessions')
            self.assertEqual(installed.minimum_jamb,100)
        updated=RuleSet.objects.get(programme='Accountancy')
        updated.minimum_jamb=110
        updated.save()
        call_command('load_compendium',verbosity=0)
        updated.refresh_from_db()
        self.assertEqual(updated.minimum_jamb,110)
        self.assertEqual(RuleSet.objects.count(),29)
        record.refresh_from_db()
        self.assertEqual(record.result,old)
