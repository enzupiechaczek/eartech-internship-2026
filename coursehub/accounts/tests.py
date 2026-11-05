from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.views import View
from accounts.decorators import instructor_required
from accounts.decorators import InstructorRequiredMixin


# --- Dummy views for testing ---

@instructor_required
def dummy_view(request):
    return HttpResponse("OK")


class DummyViewClass(InstructorRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("OK")


# --- Role Checks Test Case ---

class RoleChecksTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.instructor = User.objects.create_user(
            username='instructor_test',
            password='Password123!',
            role='INSTRUCTOR'
        )
        self.student = User.objects.create_user(
            username='student_test',
            password='Password123!',
            role='STUDENT'
        )

    # --- Decorator Tests ---

    def test_instructor_access(self):
        request = self.factory.get('/dummy/')
        request.user = self.instructor
        response = dummy_view(request)
        self.assertEqual(response.status_code, 200)

    def test_student_access_forbidden(self):
        request = self.factory.get('/dummy/')
        request.user = self.student
        with self.assertRaises(PermissionDenied):
            dummy_view(request)

    def test_anonymous_redirect(self):
        request = self.factory.get('/dummy/')
        request.user = AnonymousUser()
        response = dummy_view(request)
        self.assertEqual(response.status_code, 302)

    # --- Mixin Tests ---

    def test_mixin_instructor_access(self):
        request = self.factory.get('/dummy/')
        request.user = self.instructor
        response = DummyViewClass.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_mixin_student_access_forbidden(self):
        request = self.factory.get('/dummy/')
        request.user = self.student
        with self.assertRaises(PermissionDenied):
            DummyViewClass.as_view()(request)

    def test_mixin_anonymous_redirect(self):
        request = self.factory.get('/dummy/')
        request.user = AnonymousUser()
        response = DummyViewClass.as_view()(request)
        self.assertEqual(response.status_code, 302)
        
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



    def test_instructor_registration(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'instructor_test',
                'email': 'instructor@test.com',
                'role': User.Role.INSTRUCTOR,
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            }
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='instructor_test')
        self.assertEqual(user.role, User.Role.INSTRUCTOR)
