from django.test import TestCase
from django.urls import reverse
from decimal import Decimal
from django.contrib.auth import get_user_model
from .models import Course, Module, Lesson

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
            price=Decimal("49"), is_published=True,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Python for Beginners")
        self.assertContains(response, "by Omar Ali")
        self.assertContains(response, "$49.00")

    def test_instructor_without_full_name_shows_username(self):
        sami = get_user_model().objects.create_user(username="sami", password="pass")
        Course.objects.create(title="Cyber 101", instructor=sami, is_published=True)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "by sami")

    def test_zero_price_shows_free(self):
        Course.objects.create(
            title="Cyber 101", instructor=self.omar,
            price=Decimal("0"), is_published=True,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Free")

    def test_draft_courses_hidden(self):
        Course.objects.create(title="Draft Course", instructor=self.omar, is_published=False)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Draft Course")

    def test_placeholder_when_no_thumbnail(self):
        Course.objects.create(title="No Image", instructor=self.omar, is_published=True)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "placehold.co")

    def test_limits_to_eight_courses(self):
        for i in range(10):
            Course.objects.create(title=f"Course {i}", instructor=self.omar, is_published=True)
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
            is_published=True,
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
