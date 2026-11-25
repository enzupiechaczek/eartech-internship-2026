from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from courses.models import Course, Lesson, LessonProgress, Module
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
            role=User.Role.STUDENT,
        )
        self.other_student = User.objects.create_user(
            username="other_student",
            password="testpass123",
            role=User.Role.STUDENT,
        )

        self.course = Course.objects.create(
            title="Django Fundamentals",
            instructor=self.instructor,
            description="An introductory Django course.",
            status=Course.Status.PUBLISHED,
        )

        self.module = Module.objects.create(
            course=self.course,
            title="Introduction",
            order=1,
        )

        # Four lessons make the 50% threshold easy to test:
        # 1 completed = 25%, 2 completed = 50%.
        self.lessons = [
            Lesson.objects.create(
                module=self.module,
                title=f"Lesson {number}",
                order=number,
            )
            for number in range(1, 5)
        ]

        Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        # Expected endpoint:
        # path("course/<int:course_id>/review/", ..., name="create_review")
        self.review_url = reverse(
            "reviews:create_review",
            kwargs={"course_id": self.course.pk},
        )

        self.outline_url = reverse(
            "courses:outline",
            args=[self.course.pk],
        )

    def complete_lessons(self, count):
        for lesson in self.lessons[:count]:
            LessonProgress.objects.create(
                student=self.student,
                lesson=lesson,
            )

    def submit_review(self, rating=5, comment="Excellent course"):
        return self.client.post(
            self.review_url,
            {
                "rating": rating,
                "comment": comment,
            },
        )

    def test_student_can_submit_review_at_exactly_50_percent(self):
        self.client.login(
            username="review_student",
            password="testpass123",
        )
        self.complete_lessons(2)

        response = self.submit_review(
            rating=5,
            comment="Very useful course.",
        )

        self.assertRedirects(response, self.outline_url)

        review = Review.objects.get(
            course=self.course,
            student=self.student,
        )
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "Very useful course.")

    def test_student_can_submit_review_above_50_percent(self):
        self.client.login(
            username="review_student",
            password="testpass123",
        )
        self.complete_lessons(3)

        response = self.submit_review()

        self.assertRedirects(response, self.outline_url)
        self.assertTrue(
            Review.objects.filter(
                course=self.course,
                student=self.student,
            ).exists()
        )

    def test_student_cannot_submit_review_below_50_percent(self):
        self.client.login(
            username="review_student",
            password="testpass123",
        )
        self.complete_lessons(1)

        response = self.submit_review()

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Review.objects.filter(
                course=self.course,
                student=self.student,
            ).exists()
        )

    def test_student_cannot_review_without_enrollment(self):
        self.client.login(
            username="other_student",
            password="testpass123",
        )

        # Even completing lessons must not bypass enrollment.
        self.complete_lessons(0)

        response = self.submit_review()

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Review.objects.filter(
                course=self.course,
                student=self.other_student,
            ).exists()
        )

    def test_instructor_cannot_submit_review_for_own_course(self):
        self.client.login(
            username="review_instructor",
            password="testpass123",
        )

        response = self.submit_review()

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Review.objects.filter(
                course=self.course,
                student=self.instructor,
            ).exists()
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.submit_review()

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        self.assertFalse(Review.objects.exists())

    def test_invalid_rating_does_not_create_review(self):
        self.client.login(
            username="review_student",
            password="testpass123",
        )
        self.complete_lessons(2)

        for invalid_rating in (0, 6, "invalid"):
            with self.subTest(rating=invalid_rating):
                response = self.submit_review(
                    rating=invalid_rating,
                    comment="Invalid rating test",
                )

                self.assertNotEqual(response.status_code, 302)
                self.assertFalse(
                    Review.objects.filter(
                        course=self.course,
                        student=self.student,
                    ).exists()
                )

    def test_student_cannot_submit_duplicate_review(self):
        self.client.login(
            username="review_student",
            password="testpass123",
        )
        self.complete_lessons(2)

        Review.objects.create(
            course=self.course,
            student=self.student,
            rating=4,
            comment="My first review.",
        )

        response = self.submit_review(
            rating=5,
            comment="Trying to submit another review.",
        )

        self.assertEqual(
            Review.objects.filter(
                course=self.course,
                student=self.student,
            ).count(),
            1,
        )

        # The duplicate must not replace the original review.
        review = Review.objects.get(
            course=self.course,
            student=self.student,
        )
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, "My first review.")
