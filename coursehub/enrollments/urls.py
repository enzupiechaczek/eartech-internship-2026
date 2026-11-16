
from django.urls import path
from .views import (
    StudentDashboardView,
    StudentCourseDetailView,
)

app_name = "enrollments"

urlpatterns = [
    path(
        "my-learning/",
        StudentDashboardView.as_view(),
        name="student_dashboard",
    ),

    path(
        "my-learning/<int:enrollment_id>/",
        StudentCourseDetailView.as_view(),
        name="course_detail",
    ),
]
