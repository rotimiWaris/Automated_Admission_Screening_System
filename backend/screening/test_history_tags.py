from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import Verification


class HistoryTagTests(TestCase):
    def test_status_aliases_pagination_and_private_history(self):
        user = get_user_model().objects.create_user(username='tag-search')
        other = get_user_model().objects.create_user(username='other-tags')
        for index in range(53):
            Verification.objects.create(owner=user, result={
                'student': {'name': 'Applicant', 'registration_number': f'TAG-{index}'},
                'rules': {'programme': 'Accountancy'},
                'status': 'Pending Review' if index < 51 else 'Eligible' if index == 51 else 'Not Eligible'})
        Verification.objects.create(owner=other, result={'student': {'name': 'Private', 'registration_number': 'PRIVATE'}, 'status': 'Pending Review'})
        self.client.force_login(user)
        for query, count, status in [('pending', 51, 'Pending Review'), ('#PENDING', 51, 'Pending Review'),
                                     ('status:pending review', 51, 'Pending Review'), ('qualified', 1, 'Eligible'),
                                     ('eligible', 1, 'Eligible'), ('unqualified', 1, 'Not Eligible'),
                                     ('not eligible', 1, 'Not Eligible')]:
            with self.subTest(query=query):
                data = self.client.get('/api/history/', {'q': query}).json()
                self.assertEqual(data['count'], count)
                self.assertTrue(all(row['status'] == status for row in data['history']))
        second = self.client.get('/api/history/', {'q': 'pending', 'page': 2}).json()
        self.assertEqual(len(second['history']), 1)
        self.assertEqual(self.client.get('/api/history/', {'q': 'Accountancy'}).json()['count'], 53)
