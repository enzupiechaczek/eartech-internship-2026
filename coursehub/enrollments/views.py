
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from courses.models import Course
from .models import Enrollment


@login_required
@require_POST
@transaction.atomic
def enroll(request, course_id):
    # Only students can enroll
    if request.user.is_instructor:
        raise PermissionDenied

    # Only published courses can be enrolled in
    course = get_object_or_404(
        Course,
        pk=course_id,
        status=Course.Status.PUBLISHED,
    )

    # Create enrollment only if it does not already exist
    _, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
    )

    if created:
        messages.success(
            request,
            f'You have successfully enrolled in "{course.title}".'
        )
    else:
        messages.info(
            request,
            f'You are already enrolled in "{course.title}".'
        )

    return redirect("student_dashboard")
