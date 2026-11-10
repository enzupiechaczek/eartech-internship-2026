from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from courses.models import Course
from enrollments.models import Enrollment

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
