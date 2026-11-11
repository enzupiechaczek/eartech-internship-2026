from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView, UpdateView

from accounts.decorators import InstructorRequiredMixin, instructor_required
from enrollments.models import Enrollment

from .forms import CourseForm, LessonForm, ModuleForm
from .models import Course, Lesson, Module


class CourseFormMixin:
    """Shared configuration for the course create and update views."""

    form_class = CourseForm
    template_name = "courses/course_form.html"
    success_url = reverse_lazy("studio")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue

            css_class = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
            field.widget.attrs.setdefault("class", css_class)

        return form


class CourseCreateView(InstructorRequiredMixin, CourseFormMixin, CreateView):
    def form_valid(self, form):
        form.instance.instructor = self.request.user
        return super().form_valid(form)


class CourseUpdateView(InstructorRequiredMixin, CourseFormMixin, UpdateView):
    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user)

    def form_valid(self, form):
        form.instance.instructor = self.request.user
        return super().form_valid(form)


def course_list(request):
    return HttpResponse('Courses app is working ✅')



def course_outline(request, pk):
    """Public, read-only curriculum outline for a published course."""
    course = get_object_or_404(
        Course.objects.select_related("instructor", "category"),
        pk=pk,
        status=Course.Status.PUBLISHED,
    )
    modules = course.modules.prefetch_related("lessons").all()

    is_instructor = (
        request.user.is_authenticated
        and course.instructor_id == request.user.id
    )

    is_enrolled = (
        request.user.is_authenticated
        and Enrollment.objects.filter(
            student=request.user,
            course=course,
        ).exists()
    )

    return render(
        request,
        "courses/course_outline.html",
        {
            "course": course,
            "modules": modules,
            "lesson_count": sum(
                len(module.lessons.all()) for module in modules
            ),
            "is_instructor": is_instructor,
            "is_enrolled": is_enrolled,
        },
    )


def lesson_view(request, lesson_id):
    """Show lesson content only to the course instructor or enrolled students."""
    lesson = get_object_or_404(
        Lesson.objects.select_related("module__course"),
        pk=lesson_id,
    )
    course = lesson.module.course

    is_instructor = (
        request.user.is_authenticated
        and course.instructor_id == request.user.id
    )

    is_enrolled = (
        request.user.is_authenticated
        and Enrollment.objects.filter(
            student=request.user,
            course=course,
        ).exists()
    )

    if not is_instructor and not is_enrolled:
        if not request.user.is_authenticated:
            return redirect("login")

        raise PermissionDenied

    if course.status != Course.Status.PUBLISHED and not is_instructor:
        raise PermissionDenied

    return render(
        request,
        "courses/lesson_detail.html",
        {"lesson": lesson, "course": course},
    )


def home(request):
    courses = (
        Course.objects.filter(status=Course.Status.PUBLISHED)
        .select_related("instructor")
        .order_by("-created_at")[:8]
    )
    return render(request, "home.html", {"courses": courses})


def about(request):
    return render(request, "about.html")


@instructor_required
def studio(request):
    courses = (
        Course.objects.filter(instructor=request.user)
        .select_related("category")
        .order_by("-created_at")
    )
    return render(request, "courses/studio.html", {"courses": courses})


@instructor_required
def course_curriculum(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    modules = course.modules.prefetch_related("lessons").all()

    return render(
        request,
        "courses/curriculum.html",
        {
            "course": course,
            "modules": modules,
        },
    )


@instructor_required
def module_create(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    form = ModuleForm(
        request.POST or None,
        initial={"order": course.modules.count() + 1},
    )

    if request.method == "POST" and form.is_valid():
        module = form.save(commit=False)
        module.course = course
        module.save()
        messages.success(request, f'Module "{module.title}" was added.')
        return redirect("courses:curriculum", course_id=course.id)

    return render(
        request,
        "courses/module_form.html",
        {"form": form, "course": course, "module": None},
    )


@instructor_required
def module_edit(request, module_id):
    module = get_object_or_404(
        Module,
        id=module_id,
        course__instructor=request.user,
    )
    form = ModuleForm(request.POST or None, instance=module)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'Module "{module.title}" was updated.')
        return redirect("courses:curriculum", course_id=module.course_id)

    return render(
        request,
        "courses/module_form.html",
        {"form": form, "course": module.course, "module": module},
    )


@instructor_required
def module_delete(request, module_id):
    module = get_object_or_404(
        Module,
        id=module_id,
        course__instructor=request.user,
    )

    if request.method == "POST":
        title = module.title
        course_id = module.course_id
        module.delete()
        messages.success(request, f'Module "{title}" was deleted.')
        return redirect("courses:curriculum", course_id=course_id)

    return render(
        request,
        "courses/confirm_delete.html",
        {
            "object": module,
            "object_type": "Module",
            "course": module.course,
            "cancel_url": reverse("courses:curriculum", args=[module.course_id]),
        },
    )


@instructor_required
def lesson_create(request, module_id):
    module = get_object_or_404(
        Module,
        id=module_id,
        course__instructor=request.user,
    )
    form = LessonForm(
        request.POST or None,
        initial={"order": module.lessons.count() + 1},
    )

    if request.method == "POST" and form.is_valid():
        lesson = form.save(commit=False)
        lesson.module = module
        lesson.save()
        messages.success(request, f'Lesson "{lesson.title}" was added.')
        return redirect("courses:curriculum", course_id=module.course_id)

    return render(
        request,
        "courses/lesson_form.html",
        {"form": form, "course": module.course, "module": module, "lesson": None},
    )


@instructor_required
def lesson_edit(request, lesson_id):
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        module__course__instructor=request.user,
    )
    form = LessonForm(request.POST or None, instance=lesson)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'Lesson "{lesson.title}" was updated.')
        return redirect("courses:curriculum", course_id=lesson.module.course_id)

    return render(
        request,
        "courses/lesson_form.html",
        {
            "form": form,
            "course": lesson.module.course,
            "module": lesson.module,
            "lesson": lesson,
        },
    )


@instructor_required
def lesson_delete(request, lesson_id):
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        module__course__instructor=request.user,
    )

    if request.method == "POST":
        title = lesson.title
        course_id = lesson.module.course_id
        lesson.delete()
        messages.success(request, f'Lesson "{title}" was deleted.')
        return redirect("courses:curriculum", course_id=course_id)

    return render(
        request,
        "courses/confirm_delete.html",
        {
            "object": lesson,
            "object_type": "Lesson",
            "course": lesson.module.course,
            "cancel_url": reverse("courses:curriculum", args=[lesson.module.course_id]),
        },
    )


@instructor_required
@require_POST
def toggle_publish(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    if course.status == Course.Status.PUBLISHED:
        course.status = Course.Status.DRAFT
    else:
        course.status = Course.Status.PUBLISHED
    course.save(update_fields=["status"])
    return redirect("studio")
