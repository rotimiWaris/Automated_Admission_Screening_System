import importlib
import json
from types import SimpleNamespace
from django.apps import apps
from django.core import signing
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Verification, RuleSet


class DuplicateTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='duplicate-user')
        self.client.force_login(self.user)
        self.rule = RuleSet.objects.create(programme='Computing', required_subjects=[{'subject':'English Language','minimum_grade':'C6'}])
        self.draft = {'student_name':'Test Student', 'registration_number':'AB-123', 'course':'Computing', 'jamb_score':240,
                      'sittings':[{'board':'WAEC','exam_type':'School','year':2025,'subjects':[{'subject':s,'grade':'B3'} for s in ['English Language','Mathematics','Physics','Chemistry','Biology']]}], 'review_issues':[], 'confidence':95}

    def test_manual_repeat_is_rejected_and_database_enforces_identity(self):
        payload = self.draft | {'rule_id':self.rule.id,'rule_revision':self.rule.revision,'confirmed':True,'save':True}
        first = self.client.post('/api/screen/', json.dumps(payload), content_type='application/json')
        self.assertEqual(first.status_code, 200)
        payload['registration_number'] = ' a b 123 '
        second = self.client.post('/api/screen/', json.dumps(payload), content_type='application/json')
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()['existing_id'], first.json()['id'])
        self.assertEqual(Verification.objects.count(), 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Verification.objects.create(owner=self.user, result=first.json())

    def test_batch_repeated_save_and_in_file_duplicates_are_skipped(self):
        def post(drafts):
            token = signing.dumps({'document':'one','page':1,'drafts':drafts}, salt='ocr-batch')
            return self.client.post('/api/screen-batch/', json.dumps({'pages':[token], 'course_rules':{'Computing':{'id':self.rule.id,'revision':1}},'save':True}), content_type='application/json')
        self.assertEqual(post([self.draft,self.draft]).json()['summary'], {'Eligible':2})
        self.assertEqual(Verification.objects.count(), 0)
        self.assertEqual(post([self.draft]).json()['summary'], {'Eligible':1})
        self.assertEqual(post([self.draft]).json()['summary'], {'Eligible':1})
        self.assertEqual(Verification.objects.count(), 1)
        self.draft['jamb_score']=50
        reassessed=post([self.draft]).json()['results'][0]
        self.assertEqual(reassessed['status'],'Not Eligible')
        self.assertTrue(reassessed['save_skipped'])
        self.assertTrue(reassessed['result']['checks'])
        self.assertEqual(Verification.objects.get().result['status'],'Eligible')
        self.assertEqual(Verification.objects.count(),1)

    def test_cleanup_retains_latest_result_and_does_not_merge_owners(self):
        other = get_user_model().objects.create_user(username='different-owner')
        records = Verification.objects.bulk_create([
            Verification(owner=self.user, result={'student':{'registration_number':'ab-123'},'status':'old'}),
            Verification(owner=self.user, result={'student':{'registration_number':'AB123'},'status':'new'}),
            Verification(owner=other, result={'student':{'registration_number':'AB123'},'status':'private'})])
        migration = importlib.import_module('screening.migrations.0002_unique_student_history')
        migration.deduplicate(apps, SimpleNamespace(connection=SimpleNamespace(alias='default')))
        self.assertFalse(Verification.objects.filter(id=records[0].id).exists())
        self.assertEqual(Verification.objects.get(owner=self.user).result['status'], 'new')
        self.assertTrue(Verification.objects.filter(owner=other).exists())
