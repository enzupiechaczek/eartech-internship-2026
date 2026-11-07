from django.urls import path

from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='list'),
    path("new/", views.course_create, name="course_create"),
    path("<int:course_pk>/", views.course_detail, name="course_detail"),
    path(
        "<int:course_pk>/modules/new/",
        views.module_create,
        name="module_create",
    ),
    path("modules/<int:module_pk>/edit/", views.module_update, name="module_update"),
    path("modules/<int:module_pk>/delete/", views.module_delete, name="module_delete"),
    path(
        "modules/<int:module_pk>/lessons/new/",
        views.lesson_create,
        name="lesson_create",
    ),
    path("lessons/<int:lesson_pk>/edit/", views.lesson_update, name="lesson_update"),
    path("lessons/<int:lesson_pk>/delete/", views.lesson_delete, name="lesson_delete"),
]