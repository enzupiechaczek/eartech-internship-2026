from django.views.generic import DetailView, ListView

from accounts.decorators import StudentRequiredMixin
from .models import Enrollment


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
