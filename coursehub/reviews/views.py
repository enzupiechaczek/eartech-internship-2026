from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from courses.models import Course
from enrollments.models import Enrollment

from .forms import ReviewForm
from .models import Review


@login_required
@require_POST
def create_review(request, course_id):
    # Only students can submit reviews.
    if request.user.role != request.user.Role.STUDENT:
        raise PermissionDenied

    course = get_object_or_404(
        Course,
        pk=course_id,
        status=Course.Status.PUBLISHED,
    )

    # Verify enrollment on the server.
    is_enrolled = Enrollment.objects.filter(
        student=request.user,
        course=course,
    ).exists()

    if not is_enrolled:
        raise PermissionDenied

    # Verify exact course completion (at least 50%).
    if not course.has_completed_at_least(request.user, 50):
        messages.error(
            request,
            "You must complete at least 50% of the course to submit a review.",
        )
        return redirect("courses:outline", pk=course.pk)

    # Enforce one review per student per course.
    if Review.objects.filter(
        student=request.user,
        course=course,
    ).exists():
        messages.warning(request, "You have already reviewed this course.")
        return redirect("courses:outline", pk=course.pk)

    form = ReviewForm(request.POST)

    if form.is_valid():
        review = form.save(commit=False)
        review.student = request.user
        review.course = course
        review.save()

        messages.success(request, "Your review was submitted successfully!")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    return redirect("courses:outline", pk=course.pk)
