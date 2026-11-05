from django.urls import path

from courses.views import home
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='list'),
    path("", home, name="home"),
]