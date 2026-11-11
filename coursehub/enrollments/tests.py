from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from courses.models import Course
from enrollments.models import Enrollment
from django.urls import reverse

User = get_user_model()

class EnrollmentModelTest(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(username='instructor', password='password123')
        self.student = User.objects.create_user(username='student1', password='password123')
        self.course = Course.objects.create(title='Django Bootcamp', instructor=self.instructor)

    def test_enrollment_creation(self):
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        self.assertEqual(str(enrollment), f"{self.student} -> {self.course}")

    def test_unique_enrollment_constraint(self):
        Enrollment.objects.create(student=self.student, course=self.course)

        # Should raise IntegrityError due to unique_together constraint
        with self.assertRaises(IntegrityError):
            Enrollment.objects.create(student=self.student, course=self.course)

@override_settings(
    ROOT_URLCONF="enrollments.test_urls",
    LOGIN_URL="/login/",
)
class EnrollmentViewTest(TestCase):

    def setUp(self):
        self.instructor = User.objects.create_user(
            username="instructor_view",
            password="password123",
            role=User.Role.INSTRUCTOR,
        )
        self.student = User.objects.create_user(
            username="student_view",
            password="password123",
        )
        self.course = Course.objects.create(
            title="Django Bootcamp",
            description="Learn Django basics.",
            instructor=self.instructor,
            status=Course.Status.PUBLISHED,
        )
        self.enroll_url = reverse(
            "enrollments:enroll_course",
            args=[self.course.pk],
        )

    def test_student_can_enroll_in_published_course(self):
        self.client.login(username="student_view", password="password123")

        response = self.client.post(self.enroll_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("student_dashboard"))
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student,
                course=self.course,
            ).exists()
        )

    def test_duplicate_enrollment_does_not_create_another_record(self):
        self.client.login(username="student_view", password="password123")

        self.client.post(self.enroll_url)
        self.client.post(self.enroll_url)

        self.assertEqual(
            Enrollment.objects.filter(
                student=self.student,
                course=self.course,
            ).count(),
            1,
        )

    def test_get_request_is_not_allowed(self):
        self.client.login(username="student_view", password="password123")

        response = self.client.get(self.enroll_url)

        self.assertEqual(response.status_code, 405)

    def test_anonymous_user_cannot_enroll(self):
        response = self.client.post(self.enroll_url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Enrollment.objects.exists())

    def test_instructor_cannot_enroll(self):
        self.client.login(
            username="instructor_view",
            password="password123",
        )

        response = self.client.post(self.enroll_url)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Enrollment.objects.exists())

    def test_student_cannot_enroll_in_draft_course(self):
        self.client.login(username="student_view", password="password123")

        draft_course = Course.objects.create(
            title="Draft Course",
            description="This course is not published.",
            instructor=self.instructor,
            status=Course.Status.DRAFT,
        )

        draft_url = reverse(
            "enrollments:enroll_course",
            args=[draft_course.pk],
        )

        response = self.client.post(draft_url)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Enrollment.objects.exists())
