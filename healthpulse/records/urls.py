from django.urls import path
from . import views

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
        "appointments/<int:appointment_id>/encounter/create/",
        views.encounter_create,
        name="encounter_create",
    ),
    path(
        "encounters/<int:encounter_id>/edit/",
        views.encounter_edit,
        name="encounter_edit",
    ),
    path(
        "appointments/<int:pk>/start/",
        views.start_visit,
        name="start_visit",
    ),
]
