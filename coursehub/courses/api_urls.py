from django.urls import path
from . import views

app_name = "courses_api"

urlpatterns = [
    path("lessons/<int:lesson_id>/complete/", views.complete_lesson, name="complete_lesson"),
]