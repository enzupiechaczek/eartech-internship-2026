from django.http import HttpResponse
from django.shortcuts import render

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
    DetailView
)

from .models import Course, Module, Lesson

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

class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = "courses/course_detail.html"  # Your template path
    context_object_name = "course"

    def get_queryset(self):
        # Restricts visibility: Instructors can only view their own courses
        return Course.objects.filter(instructor=self.request.user)


class ModuleCreateView(LoginRequiredMixin, CreateView):
    model = Module
    fields = ["title", "order"]

    def form_valid(self, form):
        course = Course.objects.get(pk=self.kwargs["course_id"])

        if course.instructor != self.request.user:
            return self.handle_no_permission()

        form.instance.course = course
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "courses:course_detail",
            kwargs={"pk": self.object.course.pk}
        )

class LessonCreateView(LoginRequiredMixin, CreateView):
    model = Lesson
    fields = [
        "title",
        "notes",
        "video_url",
        "order",
    ]

    def form_valid(self, form):
        module = Module.objects.get(
            pk=self.kwargs["module_id"]
        )

        if module.course.instructor != self.request.user:
            return self.handle_no_permission()

        form.instance.module = module
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "courses:course_detail",
            kwargs={"pk": self.object.module.course.pk}
        )

class ModuleUpdateView(LoginRequiredMixin, UpdateView):
    model = Module
    fields = ["title", "order"]

    def get_queryset(self):
        return Module.objects.filter(
            course__instructor=self.request.user
        )

    def get_success_url(self):
        return reverse_lazy(
            "courses:course_detail",
            kwargs={"pk": self.object.course.pk}
        )

class ModuleDeleteView(LoginRequiredMixin, DeleteView):
    model = Module

    def get_queryset(self):
        return Module.objects.filter(
            course__instructor=self.request.user
        )

    def get_success_url(self):
        return reverse_lazy(
            "courses:course_detail",
            kwargs={"pk": self.object.course.pk}
        )

class LessonUpdateView(LoginRequiredMixin, UpdateView):
    model = Lesson
    fields = [
        "title",
        "notes",
        "video_url",
        "order",
    ]

    def get_queryset(self):
        return Lesson.objects.filter(
            module__course__instructor=self.request.user
        )

    def get_success_url(self):
        return reverse_lazy(
            "courses:course_detail",
            kwargs={"pk": self.object.module.course.pk}
        )

class LessonDeleteView(LoginRequiredMixin, DeleteView):
    model = Lesson

    def get_queryset(self):
        return Lesson.objects.filter(
            module__course__instructor=self.request.user
        )

    def get_success_url(self):
        return reverse_lazy(
            "courses:course_detail",
            kwargs={"pk": self.object.module.course.pk}
        )

