from django.http import HttpResponse
from django.shortcuts import render
from .models import Course


def course_list(request):
    return HttpResponse('Courses app is working ✅')

# Create your views here.
def home(request):
    courses = (
        Course.objects.filter(is_published=True)
        .select_related("instructor")
        .order_by("-created_at")[:8]   
    )
    return render(request, "home.html", {"courses": courses})