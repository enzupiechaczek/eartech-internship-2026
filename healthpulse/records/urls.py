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
    "encounters/<int:encounter_id>/complete/",
    views.complete_encounter,
    name="complete_encounter",
    ),
]
