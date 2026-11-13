from django.db import models
from django.conf import settings

class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')  # Prevent duplicate enrollments

    def __str__(self):
        return f"{self.student} -> {self.course}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment"
            )
        ]

    def __str__(self):
        return f"{self.student} -> {self.course}"

    @property
    def total_lessons(self):
        return self.course.modules.aggregate(
            total=models.Count("lessons")
        )["total"] or 0

    @property
    def completed_lessons(self):
        return self.lesson_progress.filter(
            completed=True
        ).count()

    @property
    def progress_percentage(self):
        total = self.total_lessons

        if not total:
            return 0

        return round(
            self.completed_lessons / total * 100
        )


# class LessonProgress(models.Model):
#     enrollment = models.ForeignKey(
#         Enrollment,
#         on_delete=models.CASCADE,
#         related_name="lesson_progress"
#     )

#     lesson = models.ForeignKey(
#         "courses.Lesson",
#         on_delete=models.CASCADE,
#         related_name="student_progress"
#     )

#     completed = models.BooleanField(default=False)

#     completed_at = models.DateTimeField(
#         null=True,
#         blank=True
#     )

#     class Meta:
#         constraints = [
#             models.UniqueConstraint(
#                 fields=["enrollment", "lesson"],
#                 name="unique_enrollment_lesson_progress"
#             )
#         ]
