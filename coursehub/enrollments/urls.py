
from django.urls import path
from . import views

app_name = "enrollments"

urlpatterns = [
    path("<int:course_id>/", views.enroll, name="enroll_course"),
]
