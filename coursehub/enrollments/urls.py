
from django.urls import path
from . import views
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
    path(
        "<int:course_id>/",
        views.enroll,
        name="enroll_course",
    ),
]
