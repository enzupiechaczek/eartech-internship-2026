from django.test import TestCase
from django.urls import reverse
from accounts.models import User


class RegistrationTest(TestCase):

    def test_student_registration(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'student_test',
                'email': 'student@test.com',
                'role': User.Role.STUDENT,
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            User.objects.filter(username='student_test').exists()
        )

    def test_user_is_logged_in_after_registration(self):
        self.client.post(
            reverse('register'),
            {
                'username': 'login_test',
                'email': 'login@test.com',
                'role': User.Role.STUDENT,
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            }
        )

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_student_role_is_saved_correctly(self):
        self.client.post(
            reverse('register'),
            {
                'username': 'role_test',
                'email': 'role@test.com',
                'role': User.Role.STUDENT,
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            }
        )

        user = User.objects.get(username='role_test')

        self.assertEqual(user.role, User.Role.STUDENT)

    def test_registration_with_invalid_data(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'invalid_test',
                'email': 'invalid-email',
                'role': User.Role.STUDENT,
                'password1': '123',
                'password2': '456',
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            User.objects.filter(username='invalid_test').exists()
        )

    def test_registration_with_duplicate_username(self):
        self.client.post(
            reverse('register'),
            {
                'username': 'duplicate_test',
                'email': 'first@test.com',
                'role': User.Role.STUDENT,
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            }
        )

        response = self.client.post(
            reverse('register'),
            {
                'username': 'duplicate_test',
                'email': 'second@test.com',
                'role': User.Role.STUDENT,
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            }
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            User.objects.filter(username='duplicate_test').count(),
            1
        )

