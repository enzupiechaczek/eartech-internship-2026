from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Course, Lesson, Module


User = get_user_model()


class CurriculumManagementTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="instructor",
            password="Password123!",
            role=User.Role.INSTRUCTOR,
        )
        self.other_instructor = User.objects.create_user(
            username="other-instructor",
            password="Password123!",
            role=User.Role.INSTRUCTOR,
        )
        self.student = User.objects.create_user(
            username="student",
            password="Password123!",
        )
        self.course = Course.objects.create(
            title="Python",
            instructor=self.instructor,
        )
        self.module = Module.objects.create(
            course=self.course,
            title="Basics",
            order=1,
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            title="Variables",
            notes="Read the examples",
            video_url="https://example.com/variables",
            order=2,
        )

    def test_owner_can_create_course_module_and_lesson(self):
        self.client.force_login(self.instructor)
        response = self.client.get(reverse("courses:course_create"))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("courses:course_create"),
            {"title": "Django"},
        )
        course = Course.objects.get(title="Django")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(course.instructor, self.instructor)

        response = self.client.get(
            reverse("courses:module_create", args=[course.pk])
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("courses:module_create", args=[course.pk]),
            {"title": "First module", "order": 3},
        )
        module = Module.objects.get(course=course)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(module.order, 3)

        response = self.client.get(
            reverse("courses:lesson_create", args=[module.pk])
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("courses:lesson_create", args=[module.pk]),
            {
                "title": "First lesson",
                "notes": "Lesson notes",
                "video_url": "https://example.com/video",
                "order": 4,
            },
        )
        lesson = Lesson.objects.get(module=module)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(lesson.title, "First lesson")
        self.assertEqual(lesson.notes, "Lesson notes")
        self.assertEqual(lesson.video_url, "https://example.com/video")
        self.assertEqual(lesson.order, 4)

    def test_owner_can_edit_and_delete_module_and_lesson(self):
        self.client.force_login(self.instructor)
        response = self.client.post(
            reverse("courses:module_update", args=[self.module.pk]),
            {"title": "Updated module", "order": 5},
        )
        self.assertEqual(response.status_code, 302)
        self.module.refresh_from_db()
        self.assertEqual((self.module.title, self.module.order), ("Updated module", 5))

        response = self.client.post(
            reverse("courses:lesson_update", args=[self.lesson.pk]),
            {
                "title": "Updated lesson",
                "notes": "Updated notes",
                "video_url": "https://example.com/updated",
                "order": 6,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, "Updated lesson")
        self.assertEqual(self.lesson.notes, "Updated notes")
        self.assertEqual(self.lesson.video_url, "https://example.com/updated")
        self.assertEqual(self.lesson.order, 6)

        response = self.client.post(
            reverse("courses:lesson_delete", args=[self.lesson.pk]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Lesson.objects.filter(pk=self.lesson.pk).exists())

        response = self.client.post(
            reverse("courses:module_delete", args=[self.module.pk]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Module.objects.filter(pk=self.module.pk).exists())

    def test_foreign_instructor_cannot_edit_or_delete_module_or_lesson(self):
        self.client.force_login(self.other_instructor)
        for name, object_pk in (
            ("courses:module_update", self.module.pk),
            ("courses:lesson_update", self.lesson.pk),
        ):
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=[object_pk]))
                self.assertEqual(response.status_code, 404)

        for name, object_pk in (
            ("courses:module_delete", self.module.pk),
            ("courses:lesson_delete", self.lesson.pk),
        ):
            with self.subTest(name=name):
                response = self.client.post(reverse(name, args=[object_pk]))
                self.assertEqual(response.status_code, 404)

        self.assertTrue(Module.objects.filter(pk=self.module.pk).exists())
        self.assertTrue(Lesson.objects.filter(pk=self.lesson.pk).exists())

    def test_student_cannot_manage_curriculum(self):
        self.client.force_login(self.student)
        response = self.client.get(
            reverse("courses:module_create", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_modules_and_lessons_are_returned_in_order(self):
        later_module = Module.objects.create(
            course=self.course,
            title="Advanced",
            order=3,
        )
        earlier_lesson = Lesson.objects.create(
            module=self.module,
            title="Introduction",
            order=1,
        )
        response = self.client.get(
            reverse("courses:course_detail", args=[self.course.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(self.course.modules.all()), [self.module, later_module])
        self.assertEqual(
            list(self.module.lessons.all()),
            [earlier_lesson, self.lesson],
        )
        self.assertLess(
            response.content.index(b"Introduction"),
            response.content.index(b"Variables"),
        )

    def test_create_forms_suggest_the_next_order(self):
        self.client.force_login(self.instructor)
        response = self.client.get(
            reverse("courses:module_create", args=[self.course.pk])
        )
        self.assertContains(response, 'name="order" value="2"')

        response = self.client.get(
            reverse("courses:lesson_create", args=[self.module.pk])
        )
        self.assertContains(response, 'name="order" value="3"')

    def test_module_creation_is_limited_to_course_owner(self):
        self.client.force_login(self.other_instructor)
        response = self.client.post(
            reverse("courses:module_create", args=[self.course.pk]),
            {"title": "Not allowed", "order": 0},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Module.objects.filter(title="Not allowed").exists())
