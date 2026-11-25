from django.urls import path
from . import views

urlpatterns = [
    path("test-dashboard/", views.test_doctor_dashboard, name="test_doctor_dashboard"),
    path("doctor-dashboard/", views.doctor_dashboard, name="doctor_dashboard"),
]
