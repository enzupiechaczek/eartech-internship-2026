from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


def instructor_required(view_func):
    """
    Allow only authenticated instructors to access a function-based view.
    Anonymous users are redirected to login.
    Other authenticated users receive HTTP 403.
    """
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_instructor:
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapped_view


class InstructorRequiredMixin(LoginRequiredMixin):
    """
    Allow only authenticated instructors to access a class-based view.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.is_instructor:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)