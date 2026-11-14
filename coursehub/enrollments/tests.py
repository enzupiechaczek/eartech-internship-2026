from django.test import TestCase
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
        )

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(
            reverse("enrollments:student_dashboard")
        )

        self.assertEqual(response.status_code, 302)

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
        self.assertContains(response, "No courses")

    def test_student_sees_only_own_enrollments(self):
        own_course = Course.objects.create(
            title="Python for Beginners",
            description="Learn Python programming.",
            instructor=self.instructor,
        )

        other_course = Course.objects.create(
            title="Advanced Django",
            description="Learn advanced Django.",
            instructor=self.instructor,
        )

        own_enrollment = Enrollment.objects.create(
            student=self.student,
            course=own_course,
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
