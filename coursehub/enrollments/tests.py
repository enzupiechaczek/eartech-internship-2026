from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, Lesson, Module
from enrollments.models import Enrollment

User = get_user_model()


class EnrollmentModelTest(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="instructor",
            password="password123",
        )
        self.student = User.objects.create_user(
            username="student1",
            password="password123",
        )
        self.course = Course.objects.create(
            title="Django Bootcamp",
            description="A complete Django course.",
            instructor=self.instructor,
        )

    def test_enrollment_creation(self):
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        self.assertEqual(str(enrollment), f"{self.student} -> {self.course}")

    def test_unique_enrollment_constraint(self):
        Enrollment.objects.create(student=self.student, course=self.course)

        with self.assertRaises(IntegrityError):
            Enrollment.objects.create(student=self.student, course=self.course)


class StudentDashboardTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student1",
            password="testpass123",
        )
        self.other_student = User.objects.create_user(
            username="student2",
            password="testpass123",
        )
        self.instructor = User.objects.create_user(
            username="instructor1",
            password="testpass123",
            role="INSTRUCTOR",
        )
        self.course = Course.objects.create(
            title="Python for Beginners",
            description="Learn Python programming.",
            instructor=self.instructor,
        )

    def test_anonymous_user_redirected_to_login(self):
        dashboard_url = reverse("enrollments:student_dashboard")

        response = self.client.get(dashboard_url)

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={dashboard_url}",
            fetch_redirect_response=False,
        )

    def test_instructor_gets_403(self):
        self.client.force_login(self.instructor)

        response = self.client.get(
            reverse("enrollments:student_dashboard")
        )

        self.assertEqual(response.status_code, 403)

    def test_empty_dashboard(self):
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("enrollments:student_dashboard")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "You haven't enrolled in any courses yet.",
        )

    def test_student_sees_only_own_enrollments(self):
        other_course = Course.objects.create(
            title="Advanced Django",
            description="Learn advanced Django.",
            instructor=self.instructor,
        )

        own_enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        Enrollment.objects.create(
            student=self.other_student,
            course=other_course,
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse("enrollments:student_dashboard")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["enrollments"].count(), 1)
        self.assertEqual(
            response.context["enrollments"].first(),
            own_enrollment,
        )
        self.assertContains(response, "Python for Beginners")
        self.assertNotContains(response, "Advanced Django")

    def test_progress_starts_at_zero(self):
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("enrollments:student_dashboard")
        )

        enrollment = response.context["enrollments"].first()
        self.assertEqual(enrollment.completed_lessons, 0)
        self.assertEqual(enrollment.progress_percentage, 0)

    def test_student_can_open_own_enrollment(self):
        module = Module.objects.create(
            course=self.course,
            title="Getting Started",
            order=1,
        )
        Lesson.objects.create(
            module=module,
            title="Installing Python",
            order=1,
        )
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "enrollments:course_detail",
                kwargs={"enrollment_id": enrollment.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for Beginners")
        self.assertContains(response, "Getting Started")
        self.assertContains(response, "Installing Python")

    def test_student_cannot_open_other_student_enrollment(self):
        other_course = Course.objects.create(
            title="Other Student Course",
            description="Another student's course.",
            instructor=self.instructor,
        )
        other_enrollment = Enrollment.objects.create(
            student=self.other_student,
            course=other_course,
        )

        self.client.force_login(self.student)

        response = self.client.get(
            reverse(
                "enrollments:course_detail",
                kwargs={"enrollment_id": other_enrollment.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
