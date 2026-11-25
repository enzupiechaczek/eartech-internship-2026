from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from courses.models import (
    Course,
    Lesson,
    LessonProgress,
    Module,
)
from enrollments.models import Enrollment
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

    def test_course_outline_displays_average_rating_and_reviews(self):
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
            reverse("courses:outline", args=[self.course.pk])
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
        outline_response = self.client.get(
            reverse("courses:outline", args=[self.course.pk])
        )
        home_response = self.client.get(reverse("home"))

        self.assertEqual(outline_response.status_code, 200)
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(outline_response, "No reviews yet")
        self.assertContains(home_response, "No reviews yet")

    def test_homepage_displays_singular_review_label(self):
        Review.objects.create(
            course=self.course,
            student=self.student_one,
            rating=5,
            comment="Excellent course",
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "(1 review)")
        self.assertNotContains(response, "(1 reviews)")

    def test_draft_course_outline_returns_404(self):
        draft_course = Course.objects.create(
            title="Draft Django Course",
            instructor=self.instructor,
            description="This course is not published.",
            status=Course.Status.DRAFT,
        )

        response = self.client.get(
            reverse("courses:outline", args=[draft_course.pk])
        )

        self.assertEqual(response.status_code, 404)


class ReviewModelTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(username="teach", password="pass")
        self.student = User.objects.create_user(username="stud", password="pass")
        self.course = Course.objects.create(
            title="Django Basics",
            instructor=self.instructor,
            description="Intro course.",
            status=Course.Status.PUBLISHED,
        )

    def make_review(self, rating=5):
        return Review(course=self.course, student=self.student, rating=rating)

    def test_valid_review_is_saved(self):
        review = self.make_review(rating=4)
        review.full_clean()
        review.save()
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(str(review), "stud - Django Basics (4/5)")

    def test_rating_1_and_5_are_allowed(self):
        for rating in (1, 5):
            self.make_review(rating=rating).full_clean()

    def test_rating_0_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_review(rating=0).full_clean()

    def test_rating_6_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_review(rating=6).full_clean()

    def test_one_review_per_student_per_course(self):
        Review.objects.create(course=self.course, student=self.student, rating=5)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(course=self.course, student=self.student, rating=3)



class ReviewSubmissionTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="review_instructor",
            password="testpass123",
            role=User.Role.INSTRUCTOR,
        )
        self.student = User.objects.create_user(
            username="review_student",
            password="testpass123",
        )
        self.other_student = User.objects.create_user(
            username="other_student",
            password="testpass123",
        )

        self.course = Course.objects.create(
            title="Python Fundamentals",
            instructor=self.instructor,
            description="Learn Python.",
            status=Course.Status.PUBLISHED,
        )

        self.module = Module.objects.create(
            course=self.course,
            title="Introduction",
        )

        self.lesson_one = Lesson.objects.create(
            module=self.module,
            title="Lesson One",
        )
        self.lesson_two = Lesson.objects.create(
            module=self.module,
            title="Lesson Two",
        )

        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        self.review_url = reverse(
            "reviews:create",
            args=[self.course.pk],
        )
        self.outline_url = reverse(
            "courses:outline",
            args=[self.course.pk],
        )

    def complete_one_lesson(self):
        return LessonProgress.objects.create(
            student=self.student,
            lesson=self.lesson_one,
        )

    def create_101_lessons(self):
        lessons = [self.lesson_one, self.lesson_two]

        for number in range(3, 102):
            lessons.append(
                Lesson.objects.create(
                    module=self.module,
                    title=f"Lesson {number}",
                )
            )

        return lessons

    def complete_lessons(self, lessons, count):
        for lesson in lessons[:count]:
            LessonProgress.objects.create(
                student=self.student,
                lesson=lesson,
            )

    def test_50_out_of_101_lessons_does_not_meet_threshold(self):
        lessons = self.create_101_lessons()
        self.complete_lessons(lessons, 50)

        self.assertEqual(
            self.course.get_completion_percentage(self.student),
            50,
        )
        self.assertFalse(
            self.course.has_completed_at_least(self.student, 50)
        )

        self.client.force_login(self.student)
        response = self.client.get(self.outline_url)

        self.assertFalse(response.context["is_review_eligible"])

        response = self.client.post(
            self.review_url,
            {"rating": 5, "comment": "Good course."},
        )

        self.assertRedirects(response, self.outline_url)
        self.assertFalse(Review.objects.filter(course=self.course).exists())

    def test_51_out_of_101_lessons_meets_threshold(self):
        lessons = self.create_101_lessons()
        self.complete_lessons(lessons, 51)

        self.assertTrue(
            self.course.has_completed_at_least(self.student, 50)
        )

        self.client.force_login(self.student)
        response = self.client.get(self.outline_url)

        self.assertTrue(response.context["is_review_eligible"])

        response = self.client.post(
            self.review_url,
            {"rating": 5, "comment": "Good course."},
        )

        self.assertRedirects(response, self.outline_url)
        self.assertTrue(
            Review.objects.filter(
                course=self.course,
                student=self.student,
            ).exists()
        )

    def test_review_form_is_hidden_below_50_percent(self):
        self.client.force_login(self.student)

        response = self.client.get(self.outline_url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_review_eligible"])
        self.assertIsNone(response.context["review_form"])
        self.assertContains(response, "Complete at least 50%")

    def test_review_form_is_visible_at_exactly_50_percent(self):
        self.complete_one_lesson()
        self.client.force_login(self.student)

        response = self.client.get(self.outline_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["completion_percent"], 50)
        self.assertTrue(response.context["is_review_eligible"])
        self.assertIsNotNone(response.context["review_form"])
        self.assertContains(response, "Submit Review")

    def test_review_form_is_visible_above_50_percent(self):
        Lesson.objects.create(
            module=self.module,
            title="Lesson Three",
        )
        self.complete_one_lesson()
        LessonProgress.objects.create(
            student=self.student,
            lesson=self.lesson_two,
        )
        self.client.force_login(self.student)

        response = self.client.get(self.outline_url)

        self.assertEqual(response.context["completion_percent"], 67)
        self.assertTrue(response.context["is_review_eligible"])

    def test_successful_review_submission(self):
        self.complete_one_lesson()
        self.client.force_login(self.student)

        response = self.client.post(
            self.review_url,
            {
                "rating": 5,
                "comment": "Excellent course!",
            },
        )

        self.assertRedirects(response, self.outline_url)
        self.assertTrue(
            Review.objects.filter(
                course=self.course,
                student=self.student,
                rating=5,
                comment="Excellent course!",
            ).exists()
        )

    def test_student_below_50_percent_cannot_submit_review(self):
        self.client.force_login(self.student)

        response = self.client.post(
            self.review_url,
            {"rating": 5, "comment": "Good course."},
        )

        self.assertRedirects(response, self.outline_url)
        self.assertFalse(Review.objects.filter(course=self.course).exists())

    def test_unenrolled_student_cannot_submit_review(self):
        self.complete_one_lesson()
        Enrollment.objects.filter(student=self.student).delete()
        self.client.force_login(self.student)

        response = self.client.post(
            self.review_url,
            {"rating": 5, "comment": "Good course."},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Review.objects.filter(course=self.course).exists())

    def test_instructor_cannot_submit_review(self):
        self.client.force_login(self.instructor)

        response = self.client.post(
            self.review_url,
            {"rating": 5, "comment": "Good course."},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Review.objects.filter(course=self.course).exists())

    def test_student_cannot_submit_duplicate_review(self):
        self.complete_one_lesson()
        Review.objects.create(
            course=self.course,
            student=self.student,
            rating=4,
        )
        self.client.force_login(self.student)

        response = self.client.post(
            self.review_url,
            {"rating": 5, "comment": "Another review."},
        )

        self.assertRedirects(response, self.outline_url)
        self.assertEqual(
            Review.objects.filter(
                course=self.course,
                student=self.student,
            ).count(),
            1,
        )

    def test_invalid_rating_is_rejected(self):
        self.complete_one_lesson()
        self.client.force_login(self.student)

        response = self.client.post(
            self.review_url,
            {"rating": 6, "comment": "Invalid rating."},
        )

        self.assertRedirects(response, self.outline_url)
        self.assertFalse(Review.objects.filter(course=self.course).exists())

    def test_anonymous_user_cannot_submit_review(self):
        response = self.client.post(
            self.review_url,
            {"rating": 5, "comment": "Good course."},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(course=self.course).exists())

    def test_get_request_cannot_submit_review(self):
        self.complete_one_lesson()
        self.client.force_login(self.student)

        response = self.client.get(self.review_url)

        self.assertEqual(response.status_code, 405)
        self.assertFalse(Review.objects.filter(course=self.course).exists())

    def test_another_students_progress_does_not_count(self):
        LessonProgress.objects.create(
            student=self.other_student,
            lesson=self.lesson_one,
        )
        LessonProgress.objects.create(
            student=self.other_student,
            lesson=self.lesson_two,
        )
        self.client.force_login(self.student)

        response = self.client.get(self.outline_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["completion_percent"], 0)
        self.assertFalse(response.context["is_review_eligible"])
        self.assertIsNone(response.context["review_form"])
