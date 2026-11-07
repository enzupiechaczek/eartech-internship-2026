from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
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


@login_required
def course_curriculum(request, course_id):
    course = get_object_or_404(
        Course,
        id=course_id,
        instructor=request.user
    )

    modules = course.modules.prefetch_related("lessons").all()

    return render(
        request,
        "courses/curriculum.html",
        {
            "course": course,
            "modules": modules,
        }
    )
