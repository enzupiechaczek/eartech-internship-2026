from django.urls import path

from . import views

from django.urls import path

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='list'),
]
