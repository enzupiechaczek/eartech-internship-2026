
from django.urls import path

from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='list'),
    path('new/', views.CourseCreateView.as_view(), name='course_create'),
    path('<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_update'),
    path('<int:pk>/toggle-publish/', views.toggle_publish, name='toggle_publish'),
    path('<int:pk>/', views.course_detail, name='detail'),
]
