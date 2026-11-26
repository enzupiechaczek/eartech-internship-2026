import io
import os
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from enrollments.models import Enrollment

from .forms import CourseForm, MAX_THUMBNAIL_SIZE, validate_thumbnail_size
from .models import Category, Course, Module, Lesson, embed_url, LessonProgress

TEMP_MEDIA_ROOT = tempfile.mkdtemp()

def make_image(name="thumb.png", fmt="PNG"):
    """A real (tiny) image in memory, so Pillow accepts it."""
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "blue").save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt.lower()}")


class LessonProgressTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(username='student', password='pass')
        self.instructor = self.User.objects.create_user(username='instructor', password='pass')

        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            instructor=self.instructor,
            status=Course.Status.PUBLISHED
        )

        self.module = Module.objects.create(course=self.course, title='Module 1')
        self.lesson1 = Lesson.objects.create(module=self.module, title='Lesson 1')
        self.lesson2 = Lesson.objects.create(module=self.module, title='Lesson 2')

        Enrollment.objects.create(student=self.user, course=self.course)

    def test_completion_percentage_zero(self):
        percent = self.course.get_completion_percentage(self.user)
        self.assertEqual(percent, 0)
    def test_completion_percentage_zero_when_course_has_no_lessons(self):
        empty_course = Course.objects.create(
            title='Empty Course',
            description='Course without lessons',
            instructor=self.instructor,
            status=Course.Status.PUBLISHED
        )

        percent = empty_course.get_completion_percentage(self.user)
        self.assertEqual(percent, 0)

    def test_completion_percentage_half(self):
        LessonProgress.objects.create(student=self.user, lesson=self.lesson1)
        percent = self.course.get_completion_percentage(self.user)
        self.assertEqual(percent, 50)
    def test_completion_percentage_rounds_partial_progress(self):
        lesson3 = Lesson.objects.create(
            module=self.module,
            title='Lesson 3'
        )

        LessonProgress.objects.create(
            student=self.user,
            lesson=self.lesson1
        )

        percent = self.course.get_completion_percentage(self.user)

        self.assertEqual(percent, 33)
    def test_completion_percentage_full(self):
        LessonProgress.objects.create(student=self.user, lesson=self.lesson1)
        LessonProgress.objects.create(student=self.user, lesson=self.lesson2)
        percent = self.course.get_completion_percentage(self.user)
        self.assertEqual(percent, 100)

    def test_complete_lesson_view(self):
        self.client.login(username='student', password='pass')
        response = self.client.post(reverse('courses_api:complete_lesson', args=[self.lesson1.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['lesson'], self.lesson1.pk)
        self.assertEqual(data['percent'], 50)

    def test_non_enrolled_user_gets_403(self):
        other_user = self.User.objects.create_user(username="other", password="pass")
        self.client.login(username="other", password="pass")
        response = self.client.post(reverse('courses_api:complete_lesson', args=[self.lesson1.pk]))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_gets_401(self):
        response = self.client.post(reverse('courses_api:complete_lesson', args=[self.lesson1.pk]))
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())
        self.assertFalse(LessonProgress.objects.exists())

    def test_get_request_returns_405(self):
        self.client.login(username="student", password="pass")
        response = self.client.get(reverse('courses_api:complete_lesson', args=[self.lesson1.pk]))
        self.assertEqual(response.status_code, 405)

    def test_double_click_creates_single_record(self):
        self.client.login(username="student", password="pass")

        # first click
        response1 = self.client.post(reverse('courses_api:complete_lesson', args=[self.lesson1.pk]))
        self.assertEqual(response1.status_code, 200)
        percent1 = response1.json()["percent"]

        # second click
        response2 = self.client.post(reverse('courses_api:complete_lesson', args=[self.lesson1.pk]))
        self.assertEqual(response2.status_code, 200)
        percent2 = response2.json()["percent"]

        # should only have one progress record
        self.assertEqual(LessonProgress.objects.filter(student=self.user, lesson=self.lesson1).count(), 1)
        # percentage should be the same
        self.assertEqual(percent1, percent2)

    def test_enrolled_student_cannot_complete_unpublished_course(self):
        draft_course = Course.objects.create(
            title='Draft Course',
            description='Draft',
            instructor=self.instructor,
            status=Course.Status.DRAFT
        )

        draft_module = Module.objects.create(course=draft_course, title='Draft Module')
        draft_lesson = Lesson.objects.create(module=draft_module, title='Draft Lesson')

        Enrollment.objects.create(student=self.user, course=draft_course)

        self.client.login(username='student', password='pass')
        response = self.client.post(reverse('courses_api:complete_lesson', args=[draft_lesson.pk]))
        self.assertEqual(response.status_code, 403)

    def test_enrolled_student_sees_progress_bar_and_button(self):
        self.client.login(username='student', password='pass')
        response = self.client.get(reverse('courses:lesson_view', args=[self.lesson1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'progress-bar')
        self.assertContains(response, 'complete-btn')
        self.assertContains(response, 'Mark as Complete')

    def test_instructor_does_not_see_progress_controls(self):
        self.client.login(username='instructor', password='pass')
        response = self.client.get(reverse('courses:lesson_view', args=[self.lesson1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'progress-bar')
        self.assertNotContains(response, 'complete-btn')

    def test_complete_lesson_shows_completed_state(self):
        LessonProgress.objects.create(student=self.user, lesson=self.lesson1)

        self.client.login(username='student', password='pass')
        response = self.client.get(reverse('courses:lesson_view', args=[self.lesson1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Completed')
        self.assertContains(response, 'disabled')

    def test_instructor_cannot_complete_lesson(self):
        self.client.login(username='instructor', password='pass')
        response = self.client.post(reverse('courses_api:complete_lesson', args=[self.lesson1.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LessonProgress.objects.filter(student=self.instructor, lesson=self.lesson1).exists())

    def test_completion_percentage_isolated_per_student(self):
        other_student = self.User.objects.create_user(username="other_student", password="pass")
        Enrollment.objects.create(student=other_student, course=self.course)

        LessonProgress.objects.create(student=self.user, lesson=self.lesson1)

        percent1 = self.course.get_completion_percentage(self.user)
        self.assertEqual(percent1, 50)

        percent2 = self.course.get_completion_percentage(other_student)
        self.assertEqual(percent2, 0)


class LessonEmbedUrlTests(TestCase):
    def test_youtube_watch_url(self):
        self.assertEqual(
            embed_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
        )

    def test_youtu_be_url(self):
        self.assertEqual(
            embed_url("https://youtu.be/dQw4w9WgXcQ"),
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
        )

    def test_vimeo_url(self):
        self.assertEqual(
            embed_url("https://vimeo.com/123456789"),
            "https://player.vimeo.com/video/123456789",
        )

    def test_invalid_url_returns_none(self):
        self.assertIsNone(embed_url("https://example.com/not-a-video"))

    def test_curriculum_shows_embed_for_valid_video(self):
        User = get_user_model()
        instructor = User.objects.create_user(
            username="owner",
            password="testpass123",
            role="INSTRUCTOR",
        )
        course = Course.objects.create(
            title="Django for Beginners",
            instructor=instructor,
            status=Course.Status.PUBLISHED,
        )
        module = Module.objects.create(course=course, title="Intro", order=1)
        Lesson.objects.create(
            module=module,
            title="Lesson 1",
            notes="Intro notes",
            video_url="https://youtu.be/dQw4w9WgXcQ",
            order=1,
        )

        self.client.login(username="owner", password="testpass123")
        response = self.client.get(
            reverse("courses:curriculum", args=[course.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://www.youtube.com/embed/dQw4w9WgXcQ")
        self.assertContains(response, "<iframe")

    def test_curriculum_shows_friendly_message_for_invalid_video(self):
        User = get_user_model()
        instructor = User.objects.create_user(
            username="owner2",
            password="testpass123",
            role="INSTRUCTOR",
        )
        course = Course.objects.create(
            title="Invalid Video Course",
            instructor=instructor,
            status=Course.Status.PUBLISHED,
        )
        module = Module.objects.create(course=course, title="Intro", order=1)
        Lesson.objects.create(
            module=module,
            title="Broken Lesson",
            notes="Oops",
            video_url="https://example.com/not-a-video",
            order=1,
        )

        self.client.login(username="owner2", password="testpass123")
        response = self.client.get(
            reverse("courses:curriculum", args=[course.id])
        )

        self.assertContains(response, "Video link is not valid")


class AboutPageTests(TestCase):
    def test_about_page_status_code_and_template(self):
        url = reverse("about")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "about.html")
        self.assertContains(response, 'href="/about/"')


class CourseListViewTests(TestCase):
    def test_course_list_page_loads(self):
        response = self.client.get(reverse('courses:list'))
        self.assertEqual(response.status_code, 200)

class HomeViewTests(TestCase):
    def setUp(self):
        self.omar = get_user_model().objects.create_user(
            username="omar",
            password="pass",
            first_name="Omar",
            last_name="Ali",
        )

    def test_home_page_loads(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")

    def test_card_shows_title_instructor_and_price(self):
        Course.objects.create(
            title="Python for Beginners", instructor=self.omar,
            price=Decimal("49"), status="PUBLISHED",
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Python for Beginners")
        self.assertContains(response, "by Omar Ali")
        self.assertContains(response, "$49.00")

    def test_instructor_without_full_name_shows_username(self):
        sami = get_user_model().objects.create_user(username="sami", password="pass")
        Course.objects.create(title="Cyber 101", instructor=sami, status="PUBLISHED")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "by sami")

    def test_zero_price_shows_free(self):
        Course.objects.create(
            title="Cyber 101", instructor=self.omar,
            price=Decimal("0"), status="PUBLISHED",
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Free")

    def test_draft_courses_hidden(self):
        Course.objects.create(title="Draft Course", instructor=self.omar, status="DRAFT")
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Draft Course")

    def test_placeholder_when_no_thumbnail(self):
        Course.objects.create(title="No Image", instructor=self.omar, status="PUBLISHED")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "placehold.co")

    def test_limits_to_eight_courses(self):
        for i in range(10):
            Course.objects.create(title=f"Course {i}", instructor=self.omar, status="PUBLISHED")
        response = self.client.get(reverse("home"))
        self.assertEqual(len(response.context["courses"]), 8)

    def test_empty_state(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "No courses yet.")

    def create_popular_test_course(self, title, status=Course.Status.PUBLISHED):
        return Course.objects.create(
            title=title,
            description="Test course",
            instructor=self.omar,
            status=status,
        )

    def add_test_enrollments(self, course, count, prefix):
        for i in range(count):
            student = get_user_model().objects.create_user(
                username=f"{prefix}_{i}",
                password="pass",
            )
            Enrollment.objects.create(student=student, course=course)

    def test_popular_courses_order_by_enrollment_count_and_creation_date(self):
        popular = self.create_popular_test_course("Most Popular")
        older_tie = self.create_popular_test_course("Older Tie")
        newer_tie = self.create_popular_test_course("Newer Tie")

        self.add_test_enrollments(popular, 2, "popular_student")
        self.add_test_enrollments(older_tie, 1, "older_student")
        self.add_test_enrollments(newer_tie, 1, "newer_student")

        now = timezone.now()
        Course.objects.filter(pk=older_tie.pk).update(
            created_at=now - timedelta(days=2)
        )
        Course.objects.filter(pk=newer_tie.pk).update(
            created_at=now - timedelta(days=1)
        )

        response = self.client.get(reverse("home"))
        popular_titles = [
            course.title
            for course in response.context["popular_courses"]
        ]

        self.assertEqual(
            popular_titles,
            ["Most Popular", "Newer Tie", "Older Tie"],
        )

    def test_popular_courses_exclude_drafts_and_limit_to_eight(self):
        for i in range(9):
            self.create_popular_test_course(f"Published Course {i}")

        draft = self.create_popular_test_course(
            "Highly Enrolled Draft",
            status=Course.Status.DRAFT,
        )
        self.add_test_enrollments(draft, 10, "draft_student")

        response = self.client.get(reverse("home"))
        popular_courses = response.context["popular_courses"]

        self.assertEqual(len(popular_courses), 8)
        self.assertTrue(
            all(
                course.status == Course.Status.PUBLISHED
                for course in popular_courses
            )
        )
        self.assertNotIn(draft, popular_courses)

class CourseCurriculumTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.instructor = User.objects.create_user(
            username="instructor1",
            password="testpass123",
            role="INSTRUCTOR",
        )

        self.other_instructor = User.objects.create_user(
            username="instructor2",
            password="testpass123",
            role="INSTRUCTOR",
        )

        self.course = Course.objects.create(
            title="Python for Beginners",
            instructor=self.instructor,
            status=Course.Status.PUBLISHED,
        )

        self.module = Module.objects.create(
            course=self.course,
            title="Introduction to Python",
            order=1,
        )

        self.lesson = Lesson.objects.create(
            module=self.module,
            title="What is Python?",
            notes="Introduction to Python programming",
            order=1,
        )

    def test_instructor_can_view_own_curriculum(self):
        self.client.login(username="instructor1", password="testpass123")

        response = self.client.get(
            reverse("courses:curriculum", args=[self.course.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for Beginners")
        self.assertContains(response, "Introduction to Python")
        self.assertContains(response, "What is Python?")

    def test_other_instructor_gets_404(self):
        self.client.login(username="instructor2", password="testpass123")

        response = self.client.get(
            reverse("courses:curriculum", args=[self.course.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(
            reverse("courses:curriculum", args=[self.course.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


class CurriculumCrudTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.instructor = User.objects.create_user(
            username="owner",
            password="testpass123",
            role="INSTRUCTOR",
        )
        self.other_instructor = User.objects.create_user(
            username="other",
            password="testpass123",
            role="INSTRUCTOR",
        )
        self.student = User.objects.create_user(
            username="student",
            password="testpass123",
            role="STUDENT",
        )

        self.course = Course.objects.create(
            title="Django for Beginners",
            instructor=self.instructor,
        )
        self.module = Module.objects.create(
            course=self.course,
            title="Getting Started",
            order=1,
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            title="Installing Python",
            notes="Setup guide",
            order=1,
        )

    def login_owner(self):
        self.client.login(username="owner", password="testpass123")

    def login_other(self):
        self.client.login(username="other", password="testpass123")

    def login_student(self):
        self.client.login(username="student", password="testpass123")

    # ----- curriculum page ------------------------------------------------

    def test_curriculum_shows_module_and_lesson_actions(self):
        self.login_owner()
        response = self.client.get(
            reverse("courses:curriculum", args=[self.course.id])
        )

        self.assertContains(response, "+ Add Module")
        self.assertContains(response, "+ Lesson")
        self.assertContains(
            response,
            reverse("courses:module_create", args=[self.course.id]),
        )
        self.assertContains(
            response,
            reverse("courses:module_edit", args=[self.module.id]),
        )
        self.assertContains(
            response,
            reverse("courses:module_delete", args=[self.module.id]),
        )
        self.assertContains(
            response,
            reverse("courses:lesson_create", args=[self.module.id]),
        )
        self.assertContains(
            response,
            reverse("courses:lesson_edit", args=[self.lesson.id]),
        )
        self.assertContains(
            response,
            reverse("courses:lesson_delete", args=[self.lesson.id]),
        )

    # ----- modules --------------------------------------------------------

    def test_module_create_form_loads(self):
        self.login_owner()
        response = self.client.get(
            reverse("courses:module_create", args=[self.course.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/module_form.html")

    def test_instructor_can_create_module(self):
        self.login_owner()
        response = self.client.post(
            reverse("courses:module_create", args=[self.course.id]),
            {"title": "Advanced Topics", "order": 2},
        )

        self.assertRedirects(
            response,
            reverse("courses:curriculum", args=[self.course.id]),
        )
        module = Module.objects.get(title="Advanced Topics")
        self.assertEqual(module.course, self.course)

    def test_module_create_requires_ownership(self):
        self.login_other()
        response = self.client.post(
            reverse("courses:module_create", args=[self.course.id]),
            {"title": "Hijacked", "order": 3},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Module.objects.filter(title="Hijacked").exists())

    def test_module_create_requires_instructor_role(self):
        self.login_student()
        response = self.client.post(
            reverse("courses:module_create", args=[self.course.id]),
            {"title": "Student module", "order": 3},
        )

        self.assertEqual(response.status_code, 403)

    def test_module_create_requires_login(self):
        response = self.client.get(
            reverse("courses:module_create", args=[self.course.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_instructor_can_edit_module(self):
        self.login_owner()
        response = self.client.post(
            reverse("courses:module_edit", args=[self.module.id]),
            {"title": "Getting Started with Django", "order": 1},
        )

        self.assertRedirects(
            response,
            reverse("courses:curriculum", args=[self.course.id]),
        )
        self.module.refresh_from_db()
        self.assertEqual(self.module.title, "Getting Started with Django")

    def test_module_edit_requires_ownership(self):
        self.login_other()
        response = self.client.post(
            reverse("courses:module_edit", args=[self.module.id]),
            {"title": "Hijacked", "order": 1},
        )

        self.assertEqual(response.status_code, 404)
        self.module.refresh_from_db()
        self.assertEqual(self.module.title, "Getting Started")

    def test_module_delete_confirmation_page(self):
        self.login_owner()
        response = self.client.get(
            reverse("courses:module_delete", args=[self.module.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/confirm_delete.html")
        self.assertContains(response, "Getting Started")
        self.assertContains(response, "Every lesson inside this module")

    def test_delete_module_get_does_not_delete(self):
        self.login_owner()
        self.client.get(
            reverse("courses:module_delete", args=[self.module.id])
        )

        self.assertTrue(Module.objects.filter(id=self.module.id).exists())

    def test_instructor_can_delete_module(self):
        self.login_owner()
        response = self.client.post(
            reverse("courses:module_delete", args=[self.module.id])
        )

        self.assertRedirects(
            response,
            reverse("courses:curriculum", args=[self.course.id]),
        )
        self.assertFalse(Module.objects.filter(id=self.module.id).exists())
        self.assertFalse(Lesson.objects.filter(id=self.lesson.id).exists())

    def test_module_delete_requires_ownership(self):
        self.login_other()
        response = self.client.post(
            reverse("courses:module_delete", args=[self.module.id])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Module.objects.filter(id=self.module.id).exists())

    # ----- lessons --------------------------------------------------------

    def test_lesson_create_form_loads(self):
        self.login_owner()
        response = self.client.get(
            reverse("courses:lesson_create", args=[self.module.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/lesson_form.html")
        self.assertContains(response, "Getting Started")

    def test_instructor_can_create_lesson(self):
        self.login_owner()
        response = self.client.post(
            reverse("courses:lesson_create", args=[self.module.id]),
            {
                "title": "Your first project",
                "notes": "Create the project",
                "video_url": "",
                "order": 2,
            },
        )

        self.assertRedirects(
            response,
            reverse("courses:curriculum", args=[self.course.id]),
        )
        lesson = Lesson.objects.get(title="Your first project")
        self.assertEqual(lesson.module, self.module)

    def test_lesson_create_requires_ownership(self):
        self.login_other()
        response = self.client.post(
            reverse("courses:lesson_create", args=[self.module.id]),
            {"title": "Hijacked lesson", "order": 2},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Lesson.objects.filter(title="Hijacked lesson").exists())

    def test_instructor_can_edit_lesson(self):
        self.login_owner()
        response = self.client.post(
            reverse("courses:lesson_edit", args=[self.lesson.id]),
            {
                "title": "Installing Python 3",
                "notes": "Updated notes",
                "video_url": "https://example.com/video",
                "order": 1,
            },
        )

        self.assertRedirects(
            response,
            reverse("courses:curriculum", args=[self.course.id]),
        )
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, "Installing Python 3")
        self.assertEqual(self.lesson.video_url, "https://example.com/video")

    def test_lesson_edit_requires_ownership(self):
        self.login_other()
        response = self.client.post(
            reverse("courses:lesson_edit", args=[self.lesson.id]),
            {"title": "Hijacked", "order": 1},
        )

        self.assertEqual(response.status_code, 404)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, "Installing Python")

    def test_lesson_delete_confirmation_page(self):
        self.login_owner()
        response = self.client.get(
            reverse("courses:lesson_delete", args=[self.lesson.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/confirm_delete.html")
        self.assertContains(response, "Installing Python")

    def test_instructor_can_delete_lesson(self):
        self.login_owner()
        response = self.client.post(
            reverse("courses:lesson_delete", args=[self.lesson.id])
        )

        self.assertRedirects(
            response,
            reverse("courses:curriculum", args=[self.course.id]),
        )
        self.assertFalse(Lesson.objects.filter(id=self.lesson.id).exists())

    def test_lesson_delete_requires_ownership(self):
        self.login_other()
        response = self.client.post(
            reverse("courses:lesson_delete", args=[self.lesson.id])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Lesson.objects.filter(id=self.lesson.id).exists())

    def test_student_cannot_delete_lessons(self):
        self.login_student()
        response = self.client.post(
            reverse("courses:lesson_delete", args=[self.lesson.id])
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Lesson.objects.filter(id=self.lesson.id).exists())

class CourseCreateUpdateTests(TestCase):
    """Course create/update views for instructors (AB#3301)."""

    def setUp(self):
        User = get_user_model()
        self.instructor = User.objects.create_user(
            username="lina",
            password="pass",
            role="INSTRUCTOR",
        )
        self.other_instructor = User.objects.create_user(
            username="omar",
            password="pass",
            role="INSTRUCTOR",
        )
        self.student = User.objects.create_user(
            username="student",
            password="pass",
            role="STUDENT",
        )
        self.category = Category.objects.get(name="Web Development")
        self.other_course = Course.objects.create(
            title="Omar's course",
            instructor=self.other_instructor,
            description="Owned by Omar.",
            category=self.category,
        )

    def login(self, username):
        self.client.login(username=username, password="pass")

    def payload(self, **overrides):
        data = {
            "title": "Django for Beginners",
            "subtitle": "Build your first web app",
            "category": self.category.pk,
            "price": "49.00",
            "description": "A beginner friendly Django course.",
            "thumbnail": "",
        }
        data.update(overrides)
        return data

    # ----- seeding --------------------------------------------------------

    def test_categories_are_seeded(self):
        names = set(Category.objects.values_list("name", flat=True))
        self.assertEqual(
            names,
            {"Web Development", "Cybersecurity", "AI", "Data"},
        )

    # ----- create ---------------------------------------------------------

    def test_create_form_loads_for_instructor(self):
        self.login("lina")
        response = self.client.get(reverse("courses:course_create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/course_form.html")
        self.assertContains(response, "Create New Course")
        self.assertContains(response, "Web Development")

    def test_instructor_can_create_course(self):
        self.login("lina")
        response = self.client.post(
            reverse("courses:course_create"),
            self.payload(),
        )

        self.assertRedirects(response, reverse("studio"))
        course = Course.objects.get(title="Django for Beginners")
        self.assertEqual(course.instructor, self.instructor)
        self.assertEqual(course.category, self.category)
        self.assertEqual(course.subtitle, "Build your first web app")
        self.assertNotEqual(course.status, "PUBLISHED")

    def test_create_sets_owner_and_ignores_posted_instructor(self):
        self.login("lina")
        self.client.post(
            reverse("courses:course_create"),
            self.payload(instructor=self.other_instructor.pk),
        )

        course = Course.objects.get(title="Django for Beginners")
        self.assertEqual(course.instructor, self.instructor)

    def test_create_requires_description(self):
        self.login("lina")
        response = self.client.post(
            reverse("courses:course_create"),
            self.payload(description=""),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Course.objects.filter(title="Django for Beginners").exists()
        )

    def test_create_rejects_thumbnail_larger_than_2_mb(self):
        self.login("lina")

        image = Image.frombytes(
            "RGB", (1500, 1500), os.urandom(1500 * 1500 * 3)
        )
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=95)
        large_image = SimpleUploadedFile(
            "large.jpg", buffer.getvalue(), content_type="image/jpeg"
        )
        self.assertGreater(large_image.size, MAX_THUMBNAIL_SIZE)

        response = self.client.post(
            reverse("courses:course_create"),
            self.payload(thumbnail=large_image),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thumbnail must be 2MB or smaller.")
        self.assertFalse(
            Course.objects.filter(title="Django for Beginners").exists()
        )

    def test_create_requires_instructor_role(self):
        self.login("student")
        response = self.client.get(reverse("courses:course_create"))

        self.assertEqual(response.status_code, 403)

    def test_create_requires_login(self):
        response = self.client.get(reverse("courses:course_create"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    # ----- update ---------------------------------------------------------

    def test_own_course_form_is_prefilled(self):
        own_course = Course.objects.create(
            title="My course",
            instructor=self.instructor,
            description="Mine.",
            category=self.category,
        )
        self.login("lina")
        response = self.client.get(
            reverse("courses:course_update", args=[own_course.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My course")
        self.assertContains(response, "Edit Course")

    def test_instructor_can_update_own_course(self):
        own_course = Course.objects.create(
            title="My course",
            instructor=self.instructor,
            description="Mine.",
            category=self.category,
        )
        self.login("lina")
        response = self.client.post(
            reverse("courses:course_update", args=[own_course.pk]),
            self.payload(title="My updated course"),
        )

        self.assertRedirects(response, reverse("studio"))
        own_course.refresh_from_db()
        self.assertEqual(own_course.title, "My updated course")
        self.assertEqual(own_course.instructor, self.instructor)

    def test_cannot_update_another_instructors_course(self):
        self.login("lina")
        response = self.client.post(
            reverse("courses:course_update", args=[self.other_course.pk]),
            self.payload(title="Hijacked"),
        )

        self.assertEqual(response.status_code, 404)
        self.other_course.refresh_from_db()
        self.assertEqual(self.other_course.title, "Omar's course")

    def test_update_missing_course_returns_404(self):
        self.login("lina")
        response = self.client.get(
            reverse("courses:course_update", args=[99999])
        )

        self.assertEqual(response.status_code, 404)

    def test_update_requires_instructor_role(self):
        self.login("student")
        response = self.client.get(
            reverse("courses:course_update", args=[self.other_course.pk])
        )

        self.assertEqual(response.status_code, 403)

    # ----- studio ---------------------------------------------------------

    def test_studio_lists_only_own_courses(self):
        Course.objects.create(
            title="Lina's course",
            instructor=self.instructor,
            description="Mine.",
            category=self.category,
        )

        Course.objects.create(
            title="Lina's second course",
            instructor=self.instructor,
            description="Another course of mine.",
            category=self.category,
        )

        self.login("lina")
        response = self.client.get(reverse("studio"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lina&#x27;s course")
        self.assertContains(response, "Lina&#x27;s second course")
        self.assertNotContains(response, "Omar&#x27;s course")

    def test_studio_requires_instructor_role(self):
        self.login("student")
        response = self.client.get(reverse("studio"))

        self.assertEqual(response.status_code, 403)

    def test_studio_requires_login(self):
        response = self.client.get(reverse("studio"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_studio_shows_curriculum_button(self):
        course = Course.objects.create(
            title="Yomna's course",
            instructor=self.instructor,
            description="Test course.",
            category=self.category,
        )

        self.login("lina")
        response = self.client.get(reverse("studio"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("courses:curriculum", args=[course.pk]),
        )

class ThumbnailSizeValidationTests(TestCase):
    def test_rejects_image_larger_than_2_mb(self):
        image = SimpleUploadedFile(
            "large.jpg",
            b"x" * (2 * 1024 * 1024 + 1),
            content_type="image/jpeg",
        )

        with self.assertRaises(ValidationError):
            validate_thumbnail_size(image)

    def test_accepts_image_smaller_than_2_mb(self):
        image = SimpleUploadedFile(
            "small.jpg",
            b"x" * 1024,
            content_type="image/jpeg",
        )
        self.assertIs(validate_thumbnail_size(image), image)

    def test_accepts_image_of_exactly_2_mb(self):
        image = SimpleUploadedFile(
            "edge.jpg",
            b"x" * MAX_THUMBNAIL_SIZE,
            content_type="image/jpeg",
        )
        self.assertIs(validate_thumbnail_size(image), image)

    def test_accepts_no_image(self):
        self.assertIsNone(validate_thumbnail_size(None))

    def test_skips_already_stored_file(self):
        # A stored file whose image is missing from disk. Reading .size would
        # raise FileNotFoundError, so the validator must not check it.
        stored = Course(thumbnail="course_thumbnails/missing.png").thumbnail
        self.assertIs(validate_thumbnail_size(stored), stored)


class TogglePublishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(
            username="teach", password="pass", role="INSTRUCTOR"
        )
        self.course = Course.objects.create(title="Django Web", instructor=self.teacher)
        self.url = reverse("courses:toggle_publish", args=[self.course.pk])

    def test_publish_then_unpublish(self):
        self.client.login(username="teach", password="pass")
        self.client.post(self.url)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, "PUBLISHED")
        self.client.post(self.url)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, "DRAFT")

    def test_other_instructor_cannot_toggle(self):
        get_user_model().objects.create_user(
            username="other", password="pass", role="INSTRUCTOR"
        )
        self.client.login(username="other", password="pass")
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        self.client.login(username="teach", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_anonymous_redirected_to_login(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_student_forbidden(self):
        get_user_model().objects.create_user(
            username="stud", password="pass", role="STUDENT"
        )
        self.client.login(username="stud", password="pass")
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, "DRAFT")


class PublicCourseOutlineTests(TestCase):
    """The public curriculum outline for a published course (AB#3313)."""

    def setUp(self):
        User = get_user_model()
        self.instructor = User.objects.create_user(
            username="lina",
            password="pass",
            role="INSTRUCTOR",
            first_name="Lina",
            last_name="Haddad",
        )
        self.course = Course.objects.create(
            title="Django for Beginners",
            subtitle="Build your first web app",
            description="A beginner friendly Django course.",
            instructor=self.instructor,
            status=Course.Status.PUBLISHED,
        )
        self.second_module = Module.objects.create(
            course=self.course, title="Models and data", order=2
        )
        self.first_module = Module.objects.create(
            course=self.course, title="Getting started", order=1
        )
        self.second_lesson = Lesson.objects.create(
            module=self.first_module, title="Install Django", order=2
        )
        self.first_lesson = Lesson.objects.create(
            module=self.first_module, title="Meet Django", order=1
        )

    def outline_url(self, course=None):
        return reverse("courses:outline", args=[(course or self.course).pk])

    # ----- public access --------------------------------------------------

    def test_guest_can_view_published_outline(self):
        response = self.client.get(self.outline_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/course_outline.html")
        self.assertContains(response, "Django for Beginners")
        self.assertContains(response, "Build your first web app")
        self.assertContains(response, "Lina Haddad")
        self.assertContains(response, "Getting started")
        self.assertContains(response, "Models and data")
        self.assertContains(response, "Meet Django")
        self.assertContains(response, "Install Django")

    def test_guest_cannot_see_lesson_notes_on_public_outline(self):
        secret_notes = "PRIVATE_NOTES_REGRESSION_CHECK"
        self.first_lesson.notes = secret_notes
        self.first_lesson.save(update_fields=["notes"])

        response = self.client.get(self.outline_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, secret_notes)

    def test_non_enrolled_student_cannot_see_lesson_notes_on_public_outline(self):
        User = get_user_model()
        student = User.objects.create_user(
            username="outline_student",
            password="testpass123",
            role="STUDENT",
        )

        secret_notes = "PRIVATE_NOTES_REGRESSION_CHECK"
        self.first_lesson.notes = secret_notes
        self.first_lesson.save(update_fields=["notes"])

        self.client.force_login(student)
        response = self.client.get(self.outline_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, secret_notes)

    def test_outline_shows_module_and_lesson_totals(self):
        response = self.client.get(self.outline_url())

        self.assertEqual(response.context["lesson_count"], 2)
        self.assertContains(response, "2 modules")
        self.assertContains(response, "2 lessons")

    def test_modules_and_lessons_are_ordered(self):
        content = self.client.get(self.outline_url()).content.decode()

        self.assertLess(
            content.index("Getting started"), content.index("Models and data")
        )
        self.assertLess(content.index("Meet Django"), content.index("Install Django"))

    def test_unknown_course_returns_404(self):
        response = self.client.get(
            reverse("courses:outline", args=[99999])
        )

        self.assertEqual(response.status_code, 404)

    # ----- draft courses stay private ------------------------------------

    def test_draft_course_returns_404_for_guest(self):
        draft = Course.objects.create(
            title="Secret draft",
            instructor=self.instructor,
            status=Course.Status.DRAFT,
        )

        response = self.client.get(self.outline_url(draft))

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "Secret draft", status_code=404)

    def test_draft_course_returns_404_for_instructor(self):
        draft = Course.objects.create(
            title="Secret draft",
            instructor=self.instructor,
            status=Course.Status.DRAFT,
        )
        self.client.login(username="lina", password="pass")

        response = self.client.get(self.outline_url(draft))

        self.assertEqual(response.status_code, 404)

    # ----- read-only ------------------------------------------------------

    def test_outline_has_no_instructor_edit_controls(self):
        self.client.login(username="lina", password="pass")
        response = self.client.get(self.outline_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "+ Add Module")
        self.assertNotContains(response, "+ Lesson")
        self.assertNotContains(
            response, reverse("courses:module_create", args=[self.course.pk])
        )
        self.assertNotContains(
            response, reverse("courses:module_edit", args=[self.first_module.pk])
        )
        self.assertNotContains(
            response, reverse("courses:module_delete", args=[self.first_module.pk])
        )
        self.assertNotContains(
            response, reverse("courses:lesson_create", args=[self.first_module.pk])
        )
        self.assertNotContains(
            response, reverse("courses:lesson_edit", args=[self.first_lesson.pk])
        )
        self.assertNotContains(
            response, reverse("courses:lesson_delete", args=[self.first_lesson.pk])
        )

    def test_empty_outline_has_a_friendly_message(self):
        empty_course = Course.objects.create(
            title="Fresh course",
            instructor=self.instructor,
            status=Course.Status.PUBLISHED,
        )

        response = self.client.get(self.outline_url(empty_course))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "This course is published but its outline is still being built.",
        )

    # ----- entry point ----------------------------------------------------

    def test_home_cards_link_to_the_outline(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, self.outline_url())


class CourseOutlineCTATests(TestCase):
    """Test course outline buttons for different user states (AB#3313)."""

    def setUp(self):
        User = get_user_model()

        self.instructor = User.objects.create_user(
            username="cta_instructor",
            password="testpass123",
            role="INSTRUCTOR",
        )

        self.student = User.objects.create_user(
            username="cta_student",
            password="testpass123",
            role="STUDENT",
        )

        self.course = Course.objects.create(
            title="Django Course",
            description="Learn Django step by step.",
            instructor=self.instructor,
            status=Course.Status.PUBLISHED,
        )

        self.module = Module.objects.create(
            course=self.course,
            title="Introduction",
            order=1,
        )

        self.lesson = Lesson.objects.create(
            module=self.module,
            title="Getting Started",
            notes="Introduction to Django.",
            order=1,
        )

        self.url = reverse(
            "courses:outline",
            args=[self.course.id],
        )

    def test_instructor_sees_manage_course_button(self):
        self.client.force_login(self.instructor)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manage Course")
        self.assertContains(
            response,
            reverse("courses:curriculum", args=[self.course.id]),
        )

    def test_enrolled_student_sees_continue_learning_button(self):
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        self.client.force_login(self.student)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continue Learning")
        self.assertContains(
            response,
            reverse("courses:lesson_view", args=[self.lesson.id]),
        )

    def test_non_enrolled_student_sees_enroll_form(self):
        self.client.force_login(self.student)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enroll Now")
        self.assertContains(response, 'method="post"')
        self.assertContains(
            response,
            f'action="/enrollments/{self.course.id}/"',
        )
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_anonymous_user_sees_login_and_register_buttons(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in")
        self.assertContains(response, "Create a free account")


class LessonAccessTests(TestCase):
    """Lesson content is protected by course access checks (AB#3313)."""

    def setUp(self):
        User = get_user_model()

        self.instructor = User.objects.create_user(
            username="lesson_instructor",
            password="testpass123",
            role="INSTRUCTOR",
        )

        self.student = User.objects.create_user(
            username="lesson_student",
            password="testpass123",
            role="STUDENT",
        )

        self.other_student = User.objects.create_user(
            username="other_student",
            password="testpass123",
            role="STUDENT",
        )

        self.course = Course.objects.create(
            title="Python Course",
            description="Python lessons",
            instructor=self.instructor,
            status=Course.Status.PUBLISHED,
        )

        self.module = Module.objects.create(
            course=self.course,
            title="Introduction",
            order=1,
        )

        self.lesson = Lesson.objects.create(
            module=self.module,
            title="First Lesson",
            notes="This is protected lesson content.",
            order=1,
        )

        self.url = reverse(
            "courses:lesson_view",
            args=[self.lesson.pk],
        )

    def test_instructor_can_view_lesson(self):
        self.client.login(
            username="lesson_instructor",
            password="testpass123",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This is protected lesson content.")

    def test_enrolled_student_can_view_lesson(self):
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        self.client.login(
            username="lesson_student",
            password="testpass123",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This is protected lesson content.")

    def test_non_enrolled_student_gets_403(self):
        self.client.login(
            username="other_student",
            password="testpass123",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertNotContains(
            response,
            "This is protected lesson content.",
            status_code=403,
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        parsed = urlparse(response.url)
        self.assertEqual(parsed.path, reverse("login"))
        self.assertEqual(parse_qs(parsed.query)["next"], [self.url])

    def test_enrolled_student_cannot_view_draft_course_lesson(self):
        self.course.status = Course.Status.DRAFT
        self.course.save()

        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        self.client.login(
            username="lesson_student",
            password="testpass123",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_student_enrolled_in_other_course_gets_403(self):
        other_course = Course.objects.create(
            title="Another Course",
            description="Another description",
            instructor=self.instructor,
            status=Course.Status.PUBLISHED,
        )
        Enrollment.objects.create(
            student=self.other_student,
            course=other_course,
        )

        self.client.login(
            username="other_student",
            password="testpass123",
        )
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertNotContains(
            response,
            "This is protected lesson content.",
            status_code=403,
        )


class CourseFormThumbnailTests(TestCase):
    """Step 3: extension, real-image and size checks on the form itself."""

    def form_with(self, thumbnail=None, instance=None):
        files = {"thumbnail": thumbnail} if thumbnail else {}
        form = CourseForm(data={"title": "Python Basics"}, files=files, instance=instance)
        form.is_valid()
        return form

    # ----- allowed formats -------------------------------------------------

    def test_png_accepted(self):
        form = self.form_with(make_image("thumb.png", "PNG"))
        self.assertNotIn("thumbnail", form.errors)

    def test_jpg_accepted(self):
        form = self.form_with(make_image("thumb.jpg", "JPEG"))
        self.assertNotIn("thumbnail", form.errors)

    def test_jpeg_extension_accepted(self):
        form = self.form_with(make_image("thumb.jpeg", "JPEG"))
        self.assertNotIn("thumbnail", form.errors)

    def test_webp_extension_accepted(self):
        form = self.form_with(make_image("thumb.webp", "WEBP"))
        self.assertNotIn("thumbnail", form.errors)

    def test_uppercase_extension_accepted(self):
        form = self.form_with(make_image("PHOTO.JPG", "JPEG"))
        self.assertNotIn("thumbnail", form.errors)

    # ----- rejected formats ------------------------------------------------

    def test_gif_rejected_even_though_it_is_a_real_image(self):
        form = self.form_with(make_image("thumb.gif", "GIF"))
        self.assertIn("thumbnail", form.errors)

    def test_bmp_rejected(self):
        form = self.form_with(make_image("thumb.bmp", "BMP"))
        self.assertIn("thumbnail", form.errors)

    def test_text_file_rejected(self):
        bad = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        form = self.form_with(bad)
        self.assertIn("thumbnail", form.errors)

    def test_fake_image_with_jpg_extension_rejected(self):
        fake = SimpleUploadedFile("evil.jpg", b"not really an image", content_type="image/jpeg")
        form = self.form_with(fake)
        self.assertIn("thumbnail", form.errors)

    # ----- size ------------------------------------------------------------

    def test_size_error_shown_on_form(self):
        big = make_image()
        big.size = MAX_THUMBNAIL_SIZE + 1   # pretend it's just over the limit
        form = self.form_with(big)
        self.assertIn("2MB", " ".join(form.errors["thumbnail"]))

    def test_exactly_2_mb_accepted_on_form(self):
        edge = make_image()
        edge.size = MAX_THUMBNAIL_SIZE
        form = self.form_with(edge)
        self.assertNotIn("thumbnail", form.errors)

    # ----- optional / editing ---------------------------------------------

    def test_thumbnail_is_optional(self):
        form = self.form_with()
        self.assertNotIn("thumbnail", form.errors)

    def test_edit_without_new_file_does_not_read_stored_file(self):
        course = Course(title="Old course", thumbnail="course_thumbnails/missing.png")
        form = self.form_with(thumbnail=None, instance=course)
        self.assertNotIn("thumbnail", form.errors)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CourseThumbnailUploadViewTests(TestCase):
    """Steps 1 and 2: the form page supports uploads and the view receives request.FILES."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.instructor = get_user_model().objects.create_user(
            username="lina", password="pass", role="INSTRUCTOR",
        )
        self.category = Category.objects.get(name="Web Development")
        self.client.login(username="lina", password="pass")

    def payload(self, **overrides):
        data = {
            "title": "Django for Beginners",
            "subtitle": "Build your first web app",
            "category": self.category.pk,
            "price": "49.00",
            "description": "A beginner friendly Django course.",
            "thumbnail": "",
        }
        data.update(overrides)
        return data

    def make_course(self, **extra):
        return Course.objects.create(
            title="My course",
            instructor=self.instructor,
            description="Mine.",
            category=self.category,
            **extra,
        )

    # ----- step 1: enctype -------------------------------------------------

    def test_create_form_supports_file_upload(self):
        response = self.client.get(reverse("courses:course_create"))
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_update_form_supports_file_upload(self):
        course = self.make_course()
        response = self.client.get(reverse("courses:course_update", args=[course.pk]))
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_file_input_only_offers_allowed_types(self):
        response = self.client.get(reverse("courses:course_create"))
        self.assertContains(response, 'Only JPG, JPEG, PNG, and WEBP images are allowed.')

    # ----- step 2: request.FILES reaches the form --------------------------

    def test_create_saves_uploaded_thumbnail(self):
        response = self.client.post(
            reverse("courses:course_create"),
            self.payload(thumbnail=make_image("thumb.png")),
        )
        self.assertRedirects(response, reverse("studio"))
        course = Course.objects.get(title="Django for Beginners")
        self.assertTrue(course.thumbnail)
        self.assertTrue(course.thumbnail.name.endswith(".png"))

    def test_create_without_thumbnail_still_works(self):
        response = self.client.post(reverse("courses:course_create"), self.payload())
        self.assertRedirects(response, reverse("studio"))
        course = Course.objects.get(title="Django for Beginners")
        self.assertFalse(course.thumbnail)

    def test_update_replaces_thumbnail(self):
        course = self.make_course(thumbnail=make_image("old.png"))
        self.client.post(
            reverse("courses:course_update", args=[course.pk]),
            self.payload(title="My course", thumbnail=make_image("new.png")),
        )
        course.refresh_from_db()
        self.assertIn("new", course.thumbnail.name)

    def test_update_without_new_file_keeps_existing_thumbnail(self):
        course = self.make_course(thumbnail=make_image("keep.png"))
        old_name = course.thumbnail.name
        self.client.post(
            reverse("courses:course_update", args=[course.pk]),
            self.payload(title="Renamed course"),
        )
        course.refresh_from_db()
        self.assertEqual(course.title, "Renamed course")
        self.assertEqual(course.thumbnail.name, old_name)

    def test_update_works_when_stored_thumbnail_file_is_missing(self):
        # Real-world case: the database points to an image that isn't on disk
        # (e.g. media/ isn't shared through Git). Editing must not crash.
        course = self.make_course(thumbnail="course_thumbnails/missing.png")
        response = self.client.post(
            reverse("courses:course_update", args=[course.pk]),
            self.payload(title="Still editable"),
        )
        self.assertRedirects(response, reverse("studio"))

    # ----- step 3, end to end ----------------------------------------------

    def test_create_rejects_wrong_extension(self):
        bad = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        response = self.client.post(
            reverse("courses:course_create"), self.payload(thumbnail=bad)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("thumbnail", response.context["form"].errors)
        self.assertFalse(Course.objects.filter(title="Django for Beginners").exists())

    def test_create_rejects_fake_image(self):
        fake = SimpleUploadedFile("evil.jpg", b"not an image", content_type="image/jpeg")
        response = self.client.post(
            reverse("courses:course_create"), self.payload(thumbnail=fake)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("thumbnail", response.context["form"].errors)
        self.assertFalse(Course.objects.filter(title="Django for Beginners").exists())

    def test_rejected_upload_does_not_change_existing_thumbnail(self):
        course = self.make_course(thumbnail=make_image("keep.png"))
        old_name = course.thumbnail.name
        bad = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        self.client.post(
            reverse("courses:course_update", args=[course.pk]),
            self.payload(title="My course", thumbnail=bad),
        )
        course.refresh_from_db()
        self.assertEqual(course.thumbnail.name, old_name)


class CourseCatalogTests(TestCase):
    """AB#3327: catalogue template, normalized query, filters and paging."""

    def setUp(self):
        self.instructor = get_user_model().objects.create_user(
            username="catalog-instructor",
            password="pass",
        )

    def make_course(self, title, status=Course.Status.PUBLISHED, **kwargs):
        return Course.objects.create(
            title=title,
            description=kwargs.pop("description", "A useful course."),
            instructor=self.instructor,
            status=status,
            **kwargs,
        )

    def test_missing_and_blank_query_normalize_to_empty_string(self):
        missing = self.client.get(reverse("courses:list"))
        blank = self.client.get(reverse("courses:list"), {"q": "   "})

        self.assertEqual(missing.status_code, 200)
        self.assertTemplateUsed(missing, "courses/course_list.html")
        self.assertEqual(missing.context["q"], "")
        self.assertEqual(blank.context["q"], "")
        self.assertContains(missing, 'value=""')

    def test_query_with_surrounding_whitespace_is_normalized(self):
        response = self.client.get(reverse("courses:list"), {"q": "  Django  "})

        self.assertEqual(response.context["q"], "Django")
        self.assertContains(response, 'value="Django"')

    def test_query_filters_published_courses_case_insensitively(self):
        django = self.make_course(
            title="Django Fundamentals",
            subtitle="Web framework",
            description="Python for the web",
        )
        flask = self.make_course(title="Flask Basics")
        draft = self.make_course(title="Django Draft", status=Course.Status.DRAFT)

        by_title = self.client.get(reverse("courses:list"), {"q": "django"})
        by_subtitle = self.client.get(reverse("courses:list"), {"q": "FRAMEWORK"})
        by_description = self.client.get(reverse("courses:list"), {"q": "python"})

        for response in (by_title, by_subtitle, by_description):
            self.assertEqual(
                list(response.context["courses"]),
                [django],
            )
            self.assertNotIn(flask, response.context["courses"])
            self.assertNotIn(draft, response.context["courses"])

    def test_category_filter_and_invalid_category(self):
        programming = Category.objects.create(name="Programming")
        design = Category.objects.create(name="Design")
        python = self.make_course(title="Python", category=programming)
        ux = self.make_course(title="UX", category=design)

        filtered = self.client.get(
            reverse("courses:list"), {"category": design.pk}
        )
        self.assertEqual(list(filtered.context["courses"]), [ux])
        self.assertEqual(filtered.context["selected_category"], design)

        invalid = self.client.get(reverse("courses:list"), {"category": "abc"})
        self.assertCountEqual(invalid.context["courses"], [python, ux])
        self.assertIsNone(invalid.context["selected_category"])

    def test_unknown_numeric_category_is_ignored(self):
        python = self.make_course(title="Python")
        django = self.make_course(title="Django")

        response = self.client.get(reverse("courses:list"), {"category": "99999"})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["selected_category"])
        self.assertCountEqual(response.context["courses"], [python, django])

    def test_catalog_is_paginated(self):
        for number in range(10):
            self.make_course(title=f"Course {number}")

        first_page = self.client.get(reverse("courses:list"))
        second_page = self.client.get(reverse("courses:list"), {"page": 2})
        last_page = self.client.get(reverse("courses:list"), {"page": 999})

        self.assertEqual(len(first_page.context["courses"]), 9)
        self.assertTrue(first_page.context["page_obj"].has_next())
        self.assertEqual(len(second_page.context["courses"]), 1)
        self.assertEqual(len(last_page.context["courses"]), 1)
        self.assertContains(first_page, "page=2")

    def test_empty_state_for_query_with_no_matches(self):
        self.make_course(title="Django Fundamentals")

        response = self.client.get(reverse("courses:list"), {"q": "missing"})

        self.assertEqual(list(response.context["courses"]), [])
        self.assertContains(response, "No courses found.")

    def test_result_summary_uses_total_across_pages(self):
        for number in range(10):
            self.make_course(title=f"Python {number}")

        first_page = self.client.get(reverse("courses:list"), {"q": "Python"})
        second_page = self.client.get(
            reverse("courses:list"), {"q": "Python", "page": 2}
        )

        self.assertEqual(first_page.context["page_obj"].paginator.count, 10)
        self.assertEqual(len(first_page.context["courses"]), 9)
        self.assertEqual(len(second_page.context["courses"]), 1)
        self.assertContains(first_page, "10 courses found")
        self.assertContains(second_page, "10 courses found")

    def test_combined_search_and_category_filter(self):
        programming = Category.objects.create(name="Programming")
        design = Category.objects.create(name="Design")
        django = self.make_course(title="Django", category=programming)
        django_design = self.make_course(title="Django UX", category=design)
        flask = self.make_course(title="Flask", category=programming)
        draft = self.make_course(
            title="Django Draft",
            status=Course.Status.DRAFT,
            category=programming,
        )

        response = self.client.get(
            reverse("courses:list"),
            {"q": "django", "category": programming.pk},
        )

        self.assertEqual(list(response.context["courses"]), [django])
        self.assertNotIn(django_design, response.context["courses"])
        self.assertNotIn(flask, response.context["courses"])
        self.assertNotIn(draft, response.context["courses"])

    def test_pagination_links_preserve_both_filters(self):
        category = Category.objects.create(name="Programming")
        for number in range(10):
            self.make_course(
                title=f"Python & Django {number}", category=category
            )

        response = self.client.get(
            reverse("courses:list"),
            {"q": "Python & Django", "category": category.pk},
        )

        self.assertEqual(response.context["q"], "Python & Django")
        self.assertEqual(response.context["selected_category"], category)
        self.assertContains(
            response,
            f"q=Python%20%26%20Django&amp;category={category.pk}&amp;page=2",
        )

    def test_draft_courses_excluded_without_query(self):
        published = self.make_course(title="Published course")
        draft = self.make_course(title="Draft course", status=Course.Status.DRAFT)

        response = self.client.get(reverse("courses:list"))

        self.assertEqual(response.context["q"], "")
        self.assertEqual(list(response.context["courses"]), [published])
        self.assertNotIn(draft, response.context["courses"])
        self.assertNotContains(response, "Draft course")


class LessonDetailTemplateTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.instructor = User.objects.create_user(
            username="classroom_instructor",
            password="password123",
            role="INSTRUCTOR",
        )
        self.student = User.objects.create_user(
            username="classroom_student",
            password="password123",
            role="STUDENT",
        )
        self.course = Course.objects.create(
            title="Django Masterclass",
            instructor=self.instructor,
            status=Course.Status.PUBLISHED,
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        self.module_1 = Module.objects.create(
            course=self.course,
            title="Getting Started",
            order=1,
        )
        self.module_2 = Module.objects.create(
            course=self.course,
            title="Advanced Topics",
            order=2,
        )
        self.lesson_1 = Lesson.objects.create(
            module=self.module_1,
            title="Installation",
            notes="Step 1: Install Python\nStep 2: Install Django",
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            order=1,
        )
        self.lesson_2 = Lesson.objects.create(
            module=self.module_1,
            title="Configuration",
            notes="Set up settings.py",
            video_url="https://example.com/not-a-valid-video",
            order=2,
        )
        self.lesson_3 = Lesson.objects.create(
            module=self.module_2,
            title="Deployment",
            notes="Deploy to production",
            video_url="",
            order=1,
        )
        self.client.force_login(self.student)

    def test_sidebar_renders_course_title_modules_and_lessons(self):
        url = reverse("courses:lesson_view", args=[self.lesson_1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django Masterclass")
        self.assertContains(response, "Getting Started")
        self.assertContains(response, "Advanced Topics")
        self.assertContains(response, "Installation")
        self.assertContains(response, "Configuration")
        self.assertContains(response, "Deployment")
        self.assertContains(response, 'id="courseAccordion"')

    def test_accordion_preserves_bootstrap_and_accessibility_attributes(self):
        url = reverse("courses:lesson_view", args=[self.lesson_1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-bs-toggle="collapse"')
        self.assertContains(response, f'data-bs-target="#collapse{self.module_1.id}"')
        self.assertContains(response, 'data-bs-parent="#courseAccordion"')
        self.assertContains(response, f'aria-controls="collapse{self.module_1.id}"')
        self.assertContains(response, f'aria-labelledby="heading{self.module_1.id}"')

    def test_current_lesson_highlighted_and_module_expanded(self):
        url = reverse("courses:lesson_view", args=[self.lesson_1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "active bg-primary text-white")
        self.assertContains(response, f'id="collapse{self.module_1.id}"')
        self.assertContains(response, "collapse show")
        self.assertContains(response, "accordion-button collapsed")

    def test_valid_video_embed_renders_iframe(self):
        url = reverse("courses:lesson_view", args=[self.lesson_1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"')
        self.assertNotContains(response, "Video link is not valid")

    def test_invalid_video_embed_displays_fallback(self):
        url = reverse("courses:lesson_view", args=[self.lesson_2.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Video link is not valid")
        self.assertNotContains(response, "<iframe")

    def test_no_video_shows_no_warning(self):
        url = reverse("courses:lesson_view", args=[self.lesson_3.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Video link is not valid")
        self.assertNotContains(response, "<iframe")

    def test_lesson_notes_rendered_with_linebreaks(self):
        url = reverse("courses:lesson_view", args=[self.lesson_1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Installation")
        self.assertContains(response, "Step 1: Install Python<br>Step 2: Install Django")


class LessonCompletionFetchTests(TestCase):
    """Verify template markup, CSRF setup, progress bar, error alert, and fetch hook (AB#3324)."""

    def setUp(self):
        User = get_user_model()
        self.instructor = User.objects.create_user(
            username="fetch_instructor",
            password="password123",
            role="INSTRUCTOR",
        )
        self.student = User.objects.create_user(
            username="fetch_student",
            password="password123",
            role="STUDENT",
        )
        self.course = Course.objects.create(
            title="Async Django Course",
            instructor=self.instructor,
            status=Course.Status.PUBLISHED,
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )
        self.module = Module.objects.create(
            course=self.course,
            title="Module 1",
            order=1,
        )
        self.lesson_1 = Lesson.objects.create(
            module=self.module,
            title="Lesson One",
            order=1,
        )
        self.lesson_2 = Lesson.objects.create(
            module=self.module,
            title="Lesson Two",
            order=2,
        )
        self.lesson_url = reverse("courses:lesson_view", args=[self.lesson_1.id])
        self.complete_url = reverse("courses_api:complete_lesson", args=[self.lesson_1.id])
        self.client.force_login(self.student)

    def test_complete_button_renders_data_attributes_and_url(self):
        response = self.client.get(self.lesson_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="complete-btn"')
        self.assertContains(response, 'type="button"')
        self.assertContains(response, f'data-url="{self.complete_url}"')
        self.assertContains(response, f'data-id="{self.lesson_1.id}"')
        self.assertContains(response, "Mark as Complete")

    def test_csrf_setup_and_fetch_hook_rendered_for_enrolled_student(self):
        response = self.client.get(self.lesson_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertIn("csrftoken", response.cookies)
        self.assertContains(response, "getCsrfToken()")
        self.assertContains(response, "await fetch(url, {")
        self.assertContains(response, 'method: "POST"')
        self.assertContains(response, '"X-CSRFToken": getCsrfToken()')
        self.assertContains(response, "data.percent")
        self.assertContains(response, "data.lesson")

    def test_progress_bar_elements_and_initial_percentage_rendered(self):
        response = self.client.get(self.lesson_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="progress-bar"')
        self.assertContains(response, 'role="progressbar"')
        self.assertContains(response, 'style="width: 0%;"')
        self.assertContains(response, 'aria-valuenow="0"')
        self.assertContains(response, 'aria-valuemin="0"')
        self.assertContains(response, 'aria-valuemax="100"')
        self.assertContains(response, '<span id="progress-percent">0%</span>')

        LessonProgress.objects.create(student=self.student, lesson=self.lesson_1)
        next_response = self.client.get(
            reverse("courses:lesson_view", args=[self.lesson_2.id])
        )
        self.assertContains(next_response, 'style="width: 50%;"')
        self.assertContains(next_response, 'aria-valuenow="50"')
        self.assertContains(next_response, '<span id="progress-percent">50%</span>')

    def test_checkmark_elements_toggle_with_completion_state(self):
        incomplete_response = self.client.get(self.lesson_url)
        self.assertContains(
            incomplete_response,
            f'id="lesson-checkmark-{self.lesson_1.id}"',
        )
        self.assertContains(
            incomplete_response,
            f'id="sidebar-checkmark-{self.lesson_1.id}"',
        )
        self.assertContains(
            incomplete_response,
            'class="text-success me-1 d-none"',
        )

        LessonProgress.objects.create(student=self.student, lesson=self.lesson_1)
        completed_response = self.client.get(self.lesson_url)
        self.assertContains(
            completed_response,
            'class="text-success me-1"',
        )
        self.assertContains(
            completed_response,
            'class="badge bg-success"',
        )
        self.assertContains(completed_response, "Completed ✓")
        self.assertContains(completed_response, "disabled")
        self.assertNotContains(completed_response, 'id="complete-btn"')

    def test_error_container_and_double_click_guard_rendered(self):
        response = self.client.get(self.lesson_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="error-message"')
        self.assertContains(response, 'class="alert alert-danger mt-3 mb-0 d-none"')
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, "completeBtn.disabled = true;")
        self.assertContains(response, "completeBtn.disabled = false;")

    def test_instructor_does_not_render_completion_fetch_controls(self):
        self.client.force_login(self.instructor)
        response = self.client.get(self.lesson_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="progress-bar"')
        self.assertNotContains(response, 'id="complete-btn"')
        self.assertNotContains(response, 'id="error-message"')
        self.assertNotContains(response, "await fetch(")

    def test_csrf_protected_post_to_complete_endpoint_succeeds(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.student)

        page_response = csrf_client.get(self.lesson_url)
        csrftoken = page_response.cookies["csrftoken"].value

        api_response = csrf_client.post(
            self.complete_url,
            HTTP_X_CSRFTOKEN=csrftoken,
        )
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(
            api_response.json(),
            {"lesson": self.lesson_1.id, "percent": 50, "completed": True},
        )

        reloaded_response = csrf_client.get(self.lesson_url)
        self.assertContains(reloaded_response, '<span id="progress-percent">50%</span>')
        self.assertContains(reloaded_response, "Completed ✓")


class MarkLessonCompleteTests(TestCase):
    """Mark lesson complete: API responses, CSRF and lesson page state."""

    # Same course, lessons and enrolled student as LessonProgressTests.
    setUp = LessonProgressTests.setUp

    def complete_url(self, lesson_id):
        return reverse('courses_api:complete_lesson', args=[lesson_id])

    def csrf_client_with_token(self):
        """A CSRF-enforcing client, logged in, holding the lesson page's token."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(reverse('courses:lesson_view', args=[self.lesson1.pk]))
        return client, client.cookies['csrftoken'].value

    # ----- API ------------------------------------------------------------

    def test_unknown_lesson_returns_404(self):
        self.client.force_login(self.user)

        response = self.client.post(self.complete_url(99999))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(LessonProgress.objects.exists())

    def test_returns_json_body_and_saves_progress(self):
        self.client.force_login(self.user)

        response = self.client.post(self.complete_url(self.lesson1.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"lesson": self.lesson1.pk, "percent": 50, "completed": True},
        )
        progress = LessonProgress.objects.get()
        self.assertEqual(progress.student, self.user)
        self.assertEqual(progress.lesson, self.lesson1)

    def test_percent_increases_with_each_completed_lesson(self):
        self.client.force_login(self.user)

        first = self.client.post(self.complete_url(self.lesson1.pk))
        second = self.client.post(self.complete_url(self.lesson2.pk))

        self.assertEqual(first.json()["percent"], 50)
        self.assertEqual(second.json()["percent"], 100)

    # ----- CSRF -----------------------------------------------------------

    def test_post_without_csrf_token_returns_403(self):
        client, _ = self.csrf_client_with_token()

        response = client.post(self.complete_url(self.lesson1.pk))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(LessonProgress.objects.exists())

    def test_post_with_csrf_token_returns_200(self):
        client, token = self.csrf_client_with_token()

        response = client.post(
            self.complete_url(self.lesson1.pk),
            headers={"X-CSRFToken": token},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            LessonProgress.objects.filter(
                student=self.user, lesson=self.lesson1
            ).exists()
        )

    # ----- lesson page ----------------------------------------------------

    def test_completed_lesson_shows_completed_button_without_complete_btn(self):
        LessonProgress.objects.create(student=self.user, lesson=self.lesson1)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('courses:lesson_view', args=[self.lesson1.pk])
        )

        # Match the real button: the page script also contains "Completed ✓".
        self.assertContains(
            response,
            '<button class="btn btn-success" disabled>Completed ✓</button>',
            html=True,
        )
        self.assertNotContains(response, 'id="complete-btn"')
