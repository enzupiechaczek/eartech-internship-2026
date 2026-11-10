from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import User


def role_required(*roles):
    """
    Restrict a view to logged-in users whose role is in `roles`.

    - Anonymous users are sent to the login page.
    - Users with a different role are redirected to their own dashboard.
    - Users whose role has no dashboard (e.g. admin) get a 403.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role in roles:
                return view_func(request, *args, **kwargs)
            own_dashboard = request.user.dashboard_url_name
            if own_dashboard:
                return redirect(own_dashboard)
            raise PermissionDenied
        return _wrapped
    return decorator


doctor_required = role_required(User.Role.DOCTOR)
patient_required = role_required(User.Role.PATIENT)
