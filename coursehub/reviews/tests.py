from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from .models import Review


User = get_user_model()


class CourseRatingDisplayTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="instructor",
            password="testpass123",
        )
        self.student_one = User.objects.create_user(
            username="student_one",
            password="testpass123",
        )
        self.student_two = User.objects.create_user(
            username="student_two",
            password="testpass123",
        )

        self.course = Course.objects.create(
            title="Django Fundamentals",
            instructor=self.instructor,
            description="An introductory Django course.",
            status=Course.Status.PUBLISHED,
        )

    def test_course_detail_displays_average_rating_and_reviews(self):
        Review.objects.create(
            course=self.course,
            student=self.student_one,
            rating=5,
            comment="Excellent course",
        )
        Review.objects.create(
            course=self.course,
            student=self.student_two,
            rating=4,
            comment="Clear explanations",
        )

        response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertAlmostEqual(
            float(response.context["average_rating"]),
            4.5,
        )
        self.assertEqual(response.context["review_count"], 2)
        self.assertContains(response, "4.5/5")
        self.assertContains(response, "Excellent course")
        self.assertContains(response, "Clear explanations")

    def test_homepage_displays_average_rating_on_course_card(self):
        Review.objects.create(
            course=self.course,
            student=self.student_one,
            rating=5,
            comment="Excellent course",
        )
        Review.objects.create(
            course=self.course,
            student=self.student_two,
            rating=3,
            comment="Good introduction",
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django Fundamentals")
        self.assertContains(response, "4.0/5")
        self.assertContains(response, "(2 reviews)")

    def test_course_pages_display_message_when_there_are_no_reviews(self):
        detail_response = self.client.get(
            reverse("courses:detail", args=[self.course.pk])
        )
        home_response = self.client.get(reverse("home"))

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(detail_response, "No reviews yet")
        self.assertContains(home_response, "No reviews yet")
