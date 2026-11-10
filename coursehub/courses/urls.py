from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='list'),

    # Course Create and Edit
    path('new/', views.CourseCreateView.as_view(), name='course_create'),
    path('<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_update'),
    path(
        '<int:pk>/toggle-publish/',
        views.toggle_publish,
        name='toggle_publish',
    ),

    # Curriculum
    path(
        '<int:course_id>/curriculum/',
        views.course_curriculum,
        name='curriculum',
    ),

    # Module CRUD
    path(
        '<int:course_id>/modules/add/',
        views.module_create,
        name='module_create',
    ),
    path(
        'modules/<int:module_id>/edit/',
        views.module_edit,
        name='module_edit',
    ),
    path(
        'modules/<int:module_id>/delete/',
        views.module_delete,
        name='module_delete',
    ),

    # Lesson CRUD
    path(
        'modules/<int:module_id>/lessons/add/',
        views.lesson_create,
        name='lesson_create',
    ),
    path(
        'lessons/<int:lesson_id>/edit/',
        views.lesson_edit,
        name='lesson_edit',
    ),
    path(
        'lessons/<int:lesson_id>/delete/',
        views.lesson_delete,
        name='lesson_delete',
    ),
]
