from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import instructor_required

from .forms import CourseForm, LessonForm, ModuleForm
from .models import Course, Lesson, Module


def _next_order(queryset):
    max_order = queryset.aggregate(max_order=Max("order"))["max_order"]
    return 0 if max_order is None else max_order + 1


def course_list(request):
    courses = Course.objects.select_related("instructor")
    return render(request, "courses/course_list.html", {"courses": courses})


def course_detail(request, course_pk):
    course = get_object_or_404(
        Course.objects.prefetch_related("modules__lessons"),
        pk=course_pk,
    )
    return render(request, "courses/course_detail.html", {"course": course})


@instructor_required
def course_create(request):
    form = CourseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        course = form.save(commit=False)
        course.instructor = request.user
        course.save()
        return redirect("courses:course_detail", course_pk=course.pk)
    return render(
        request,
        "courses/course_form.html",
        {"form": form, "cancel_url": "courses:list"},
    )


@instructor_required
def module_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, instructor=request.user)
    form = ModuleForm(request.POST or None)
    form.fields["order"].initial = _next_order(course.modules.all())
    if request.method == "POST" and form.is_valid():
        module = form.save(commit=False)
        module.course = course
        module.save()
        return redirect("courses:course_detail", course_pk=course.pk)
    return render(
        request,
        "courses/object_form.html",
        {
            "form": form,
            "heading": "Add module",
            "cancel_url": "courses:course_detail",
            "cancel_kwargs": {"course_pk": course.pk},
        },
    )


@instructor_required
def module_update(request, module_pk):
    module = get_object_or_404(
        Module.objects.select_related("course"),
        pk=module_pk,
        course__instructor=request.user,
    )
    form = ModuleForm(request.POST or None, instance=module)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("courses:course_detail", course_pk=module.course_id)
    return render(
        request,
        "courses/object_form.html",
        {
            "form": form,
            "heading": "Edit module",
            "cancel_url": "courses:course_detail",
            "cancel_kwargs": {"course_pk": module.course_id},
        },
    )


@instructor_required
@require_POST
def module_delete(request, module_pk):
    module = get_object_or_404(
        Module.objects.select_related("course"),
        pk=module_pk,
        course__instructor=request.user,
    )
    course_pk = module.course_id
    module.delete()
    return redirect("courses:course_detail", course_pk=course_pk)


@instructor_required
def lesson_create(request, module_pk):
    module = get_object_or_404(
        Module.objects.select_related("course"),
        pk=module_pk,
        course__instructor=request.user,
    )
    form = LessonForm(request.POST or None)
    form.fields["order"].initial = _next_order(module.lessons.all())
    if request.method == "POST" and form.is_valid():
        lesson = form.save(commit=False)
        lesson.module = module
        lesson.save()
        return redirect("courses:course_detail", course_pk=module.course_id)
    return render(
        request,
        "courses/object_form.html",
        {
            "form": form,
            "heading": "Add lesson",
            "cancel_url": "courses:course_detail",
            "cancel_kwargs": {"course_pk": module.course_id},
        },
    )


@instructor_required
def lesson_update(request, lesson_pk):
    lesson = get_object_or_404(
        Lesson.objects.select_related("module__course"),
        pk=lesson_pk,
        module__course__instructor=request.user,
    )
    form = LessonForm(request.POST or None, instance=lesson)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(
            "courses:course_detail",
            course_pk=lesson.module.course_id,
        )
    return render(
        request,
        "courses/object_form.html",
        {
            "form": form,
            "heading": "Edit lesson",
            "cancel_url": "courses:course_detail",
            "cancel_kwargs": {"course_pk": lesson.module.course_id},
        },
    )


@instructor_required
@require_POST
def lesson_delete(request, lesson_pk):
    lesson = get_object_or_404(
        Lesson.objects.select_related("module__course"),
        pk=lesson_pk,
        module__course__instructor=request.user,
    )
    course_pk = lesson.module.course_id
    lesson.delete()
    return redirect("courses:course_detail", course_pk=course_pk)
