from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Verification


class HistoryPaginationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='history-user')
        other = get_user_model().objects.create_user(username='other-history-user')
        Verification.objects.bulk_create([Verification(owner=self.user, result={
            'student': {'name': f'Student {i}', 'registration_number': f'REG-{i}'},
            'rules': {'programme': 'Computing'}, 'status': 'Eligible'}) for i in range(125)])
        Verification.objects.create(owner=other, result={'student': {'name': 'Private Student'}})
        self.client.force_login(self.user)

    def test_every_record_is_reachable_in_pages_of_fifty(self):
        pages = [self.client.get('/api/history/', {'page': n}).json() for n in [1, 2, 3]]
        self.assertEqual([len(p['history']) for p in pages], [50, 50, 25])
        self.assertTrue(all(p['count'] == 125 and p['num_pages'] == 3 and p['page_size'] == 50 for p in pages))
        ids = [row['id'] for page in pages for row in page['history']]
        self.assertEqual(len(set(ids)), 125)
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_search_reaches_old_records_and_stays_private(self):
        result = self.client.get('/api/history/', {'q': 'REG-0'}).json()
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['history'][0]['student']['name'], 'Student 0')
        self.assertEqual(self.client.get('/api/history/', {'q': 'Private Student'}).json()['count'], 0)

    def test_invalid_empty_and_out_of_range_pages(self):
        for value in ['bad', '0', '-1']:
            self.assertEqual(self.client.get('/api/history/', {'page': value}).status_code, 400)
        self.assertEqual(self.client.get('/api/history/', {'page': 99}).json()['page'], 3)
        data = self.client.get('/api/history/', {'q': 'absent', 'page': 99}).json()
        self.assertEqual((data['page'], data['num_pages'], data['count']), (1, 1, 0))
