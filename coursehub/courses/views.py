from django import forms
from django.db.models import Avg
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView, UpdateView

from accounts.decorators import InstructorRequiredMixin, instructor_required

from .forms import CourseForm
from .models import Course


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
    return HttpResponse('Courses app is working')


def home(request):
    courses = (
        Course.objects.filter(status=Course.Status.PUBLISHED)
        .select_related("instructor", "category")
        .annotate(
            average_rating=Avg("reviews__rating"),
        )
        .order_by("-created_at")[:8]
    )
    return render(request, "home.html", {"courses": courses})


def about(request):
    return render(request, "about.html")


def course_detail(request, pk):
    course = get_object_or_404(
        Course.objects.select_related("instructor", "category"),
        pk=pk,
        status=Course.Status.PUBLISHED,
    )

    rating_summary = course.reviews.aggregate(
        average_rating=Avg("rating")
    )

    reviews = course.reviews.select_related("student").all()

    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course,
            "average_rating": rating_summary["average_rating"],
            "review_count": reviews.count(),
            "reviews": reviews,
        },
    )


@instructor_required
def studio(request):
    courses = (
        Course.objects.filter(instructor=request.user)
        .select_related("category")
        .order_by("-created_at")
    )
    return render(request, "courses/studio.html", {"courses": courses})


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
