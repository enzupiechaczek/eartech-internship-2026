from django.urls import path
from . import views
app_name = "records"

urlpatterns = [
    path(
        "patients/<int:patient_id>/chart/",
        views.patient_medical_chart,
        name="patient_medical_chart",
    ),
    path(
        "encounters/<int:encounter_id>/",
        views.encounter_detail,
        name="encounter_detail",
    ),
      path(
        "appointment/<int:pk>/start/",
        views.start_visit,
        name="start_visit",
    ),
    path(
        "appointment/<int:pk>/encounter/",
        views.encounter_form_view,
        name="encounter_form",
    ),
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    
]