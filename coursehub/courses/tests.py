import io
import os
from decimal import Decimal
import shutil
import tempfile
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .forms import MAX_THUMBNAIL_SIZE, validate_thumbnail_size, CourseForm
from .models import Category, Course, Module, Lesson

TEMP_MEDIA_ROOT = tempfile.mkdtemp()

def make_image(name="thumb.png", fmt="PNG"):
    """A real (tiny) image in memory, so Pillow accepts it."""
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "blue").save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt.lower()}")

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