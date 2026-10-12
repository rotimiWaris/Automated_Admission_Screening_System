from django.test import TestCase, Client
from django.contrib.auth import get_user_model


class AuthenticationTests(TestCase):
    def test_every_function_requires_login(self):
        for path in ['catalogue', 'rules', 'rules/1', 'screen', 'ocr', 'screen-batch', 'history', 'logout', 'future-endpoint']:
            for method in ['get', 'post', 'put']:
                with self.subTest(path=path, method=method):
                    response = getattr(self.client, method)('/api/'+path+'/')
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(self.client.get('/api/session/').status_code, 200)

    def test_login_access_logout_and_staff_permissions(self):
        get_user_model().objects.create_user(username='user',password='testing-password')
        response=self.client.post('/api/login/',{'username':'user','password':'testing-password'},content_type='application/json')
        self.assertEqual(response.status_code,200)
        for path in ['catalogue','rules','history']:
            self.assertEqual(self.client.get('/api/'+path+'/').status_code,200)
        self.assertEqual(self.client.post('/api/rules/',{},content_type='application/json').status_code,403)
        self.assertEqual(self.client.post('/api/logout/').status_code,200)
        self.assertEqual(self.client.get('/api/catalogue/').status_code,401)

    def test_login_still_requires_csrf(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/login/',{},content_type='application/json').status_code,403)
