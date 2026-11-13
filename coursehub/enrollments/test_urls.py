
from django.http import HttpResponse
from django.urls import include, path


def student_dashboard(request):
    return HttpResponse("Student dashboard")


urlpatterns = [
    path("enrollments/", include("enrollments.urls")),
    path("student-dashboard/", student_dashboard, name="student_dashboard"),
]
