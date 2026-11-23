
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, Lesson, LessonProgress, Module
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
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        with self.assertRaises(IntegrityError):
            Enrollment.objects.create(
                student=self.student,
                course=self.course,
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
        self.client.login(
            username="student_view",
            password="password123",
        )

        response = self.client.post(self.enroll_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("enrollments:student_dashboard"),
        )
        self.assertEqual(
            [str(message) for message in get_messages(response.wsgi_request)],
            ["Enrolled!"],
        )
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student,
                course=self.course,
            ).exists()
        )

    def test_duplicate_enrollment_does_not_create_another_record(self):
        self.client.login(
            username="student_view",
            password="password123",
        )

        self.client.post(self.enroll_url)
        response = self.client.post(self.enroll_url)

        self.assertEqual(
            [str(message) for message in get_messages(response.wsgi_request)],
            ["Enrolled!", "You are already enrolled."],
        )
        self.assertEqual(
            Enrollment.objects.filter(
                student=self.student,
                course=self.course,
            ).count(),
            1,
        )

    def test_get_request_is_not_allowed(self):
        self.client.login(
            username="student_view",
            password="password123",
        )

        response = self.client.get(self.enroll_url)

        self.assertEqual(response.status_code, 405)

    def test_anonymous_user_cannot_enroll(self):
        response = self.client.post(self.enroll_url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/?next="))
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
        self.client.login(
            username="student_view",
            password="password123",
        )

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

    def test_dashboard_shows_start_course_when_progress_is_zero(self):
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("enrollments:student_dashboard")
        )
        self.assertContains(response, "Start Course")

    def test_dashboard_shows_continue_when_progress_is_greater_than_zero(self):
        module = Module.objects.create(
            course=self.course,
            title="Module 1",
        )
        lesson1 = Lesson.objects.create(
            module=module,
            title="Lesson 1",
        )
        Lesson.objects.create(
            module=module,
            title="Lesson 2",
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        LessonProgress.objects.create(
            student=self.student,
            lesson=lesson1,
        )
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("enrollments:student_dashboard")
        )
        self.assertRegex(
            response.content.decode(),
            r'<a[^>]*class="btn btn-primary w-100"[^>]*>\s*Continue\s*</a>',
        )
        self.assertNotContains(response, "Start Course")

    def test_dashboard_progress_is_isolated_between_students(self):
        module = Module.objects.create(
            course=self.course,
            title="Module 1",
        )
        lesson1 = Lesson.objects.create(
            module=module,
            title="Lesson 1",
        )
        Lesson.objects.create(
            module=module,
            title="Lesson 2",
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        Enrollment.objects.create(
            student=self.other_student,
            course=self.course,
        )
        LessonProgress.objects.create(
            student=self.other_student,
            lesson=lesson1,
        )
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("enrollments:student_dashboard")
        )
        self.assertContains(response, "Start Course")

    def test_progress_updates_when_student_completes_lesson(self):
        module = Module.objects.create(
            course=self.course,
            title="Module 1",
        )
        lesson1 = Lesson.objects.create(
            module=module,
            title="Lesson 1",
        )
        Lesson.objects.create(
            module=module,
            title="Lesson 2",
        )
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        LessonProgress.objects.create(
            student=self.student,
            lesson=lesson1,
        )

        self.assertEqual(enrollment.completed_lessons, 1)
        self.assertEqual(enrollment.progress_percentage, 50)

    def test_progress_is_isolated_between_students(self):
        module = Module.objects.create(
            course=self.course,
            title="Module 1",
        )
        lesson1 = Lesson.objects.create(
            module=module,
            title="Lesson 1",
        )
        Lesson.objects.create(
            module=module,
            title="Lesson 2",
        )

        enrollment1 = Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        enrollment2 = Enrollment.objects.create(
            student=self.other_student,
            course=self.course,
        )
        LessonProgress.objects.create(
            student=self.student,
            lesson=lesson1,
        )

        self.assertEqual(enrollment1.completed_lessons, 1)
        self.assertEqual(enrollment1.progress_percentage, 50)

        self.assertEqual(enrollment2.completed_lessons, 0)
        self.assertEqual(enrollment2.progress_percentage, 0)


    def test_progress_is_isolated_between_courses(self):
        module1 = Module.objects.create(
            course=self.course,
            title="Module 1",
        )
        lesson1 = Lesson.objects.create(
            module=module1,
            title="Lesson 1",
        )
        Lesson.objects.create(
            module=module1,
            title="Lesson 2",
        )

        other_course = Course.objects.create(
            title="Java Course",
            description="Learn Java.",
            instructor=self.instructor,
        )

        module2 = Module.objects.create(
            course=other_course,
            title="Module 2",
        )
        Lesson.objects.create(
            module=module2,
            title="Lesson 3",
        )
        Lesson.objects.create(
            module=module2,
            title="Lesson 4",
        )

        enrollment1 = Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        enrollment2 = Enrollment.objects.create(
            student=self.student,
            course=other_course,
        )

        LessonProgress.objects.create(
            student=self.student,
            lesson=lesson1,
        )

        self.assertEqual(enrollment1.completed_lessons, 1)
        self.assertEqual(enrollment1.progress_percentage, 50)

        self.assertEqual(enrollment2.completed_lessons, 0)
        self.assertEqual(enrollment2.progress_percentage, 0)

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
