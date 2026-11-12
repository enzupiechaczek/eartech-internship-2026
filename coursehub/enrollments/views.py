from django.shortcuts import render

# Create your views here.

from django.views.generic import ListView, DetailView
from django.db.models import Count, Q

from accounts.decorators import StudentRequiredMixin
from .models import Enrollment


class StudentDashboardView(StudentRequiredMixin, ListView):
    """
    Display courses enrolled by the authenticated student.
    """

    model = Enrollment
    template_name = "enrollments/dashboard.html"
    context_object_name = "enrollments"
    ordering = ["-enrolled_at"]

    def get_queryset(self):
        return (
            Enrollment.objects
            .filter(student=self.request.user)
            .select_related(
                "course",
                "course__instructor",
                "course__category",
            )
            .annotate(
                total_lessons=Count(
                    "course__modules__lessons",
                    distinct=True,
                ),
                completed_lessons=Count(
                    "lesson_progress",
                    filter=Q(lesson_progress__completed=True),
                    distinct=True,
                ),
            )
            .order_by("-enrolled_at")
        )


class StudentCourseDetailView(StudentRequiredMixin, DetailView):
    """
    Display a course belonging to the authenticated student.
    """

    model = Enrollment
    template_name = "enrollments/course_detail.html"
    context_object_name = "enrollment"
    pk_url_kwarg = "enrollment_id"

    def get_queryset(self):
        return (
            Enrollment.objects
            .filter(student=self.request.user)
            .select_related(
                "course",
                "course__instructor",
            )
            .prefetch_related(
                "course__modules__lessons",
                "lesson_progress",
            )
        )
