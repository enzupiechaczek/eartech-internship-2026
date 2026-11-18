
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from accounts.decorators import StudentRequiredMixin
from courses.models import Course
from .models import Enrollment


@login_required
@require_POST
@transaction.atomic
def enroll(request, course_id):
    # Only students can enroll
    if request.user.is_instructor:
        raise PermissionDenied

    # Only published courses can be enrolled in
    course = get_object_or_404(
        Course,
        pk=course_id,
        status=Course.Status.PUBLISHED,
    )

    # Create enrollment only if it does not already exist
    _, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
    )

    if created:
        messages.success(request, "Enrolled!")
    else:
        messages.info(request, "You are already enrolled.")

    return redirect("enrollments:student_dashboard")


class StudentDashboardView(StudentRequiredMixin, ListView):
    model = Enrollment
    template_name = "enrollments/dashboard.html"
    context_object_name = "enrollments"

    def get_queryset(self):
        return (
            Enrollment.objects
            .filter(student=self.request.user)
            .select_related(
                "course",
                "course__instructor",
            )
            .order_by("-enrolled_at")
        )


class StudentCourseDetailView(StudentRequiredMixin, DetailView):
    model = Enrollment
    template_name = "enrollments/course_detail.html"
    context_object_name = "enrollment"
    pk_url_kwarg = "enrollment_id"

    def get_queryset(self):
        return (
            Enrollment.objects
            .filter(student=self.request.user)
            .select_related("course", "course__instructor")
            .prefetch_related(
                "course__modules__lessons",
            )
        )
