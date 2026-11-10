from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.urls import reverse

from .decorators import doctor_required, patient_required
from .forms import RoleRegistrationForm
from .models import PatientProfile, DoctorProfile


def register_view(request):
    if request.method == 'POST':
        form = RoleRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            if user.is_doctor:
                DoctorProfile.objects.create(user=user)
            else:
                PatientProfile.objects.create(user=user)

            login(request, user)
            return redirect(user.dashboard_url_name)
    else:
        form = RoleRegistrationForm()

    return render(request, 'register.html', {'form': form})


def home_redirect(request):
    """Send each user to the right place: login if anonymous, else their dashboard."""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.dashboard_url_name:
        return redirect(request.user.dashboard_url_name)
    if request.user.is_staff:
        return redirect('admin:index')
    raise PermissionDenied


@doctor_required
def doctor_dashboard(request):
    return render(request, 'doctor_dashboard.html')


@patient_required
def patient_dashboard(request):
    return render(request, 'patient_dashboard.html')


class RoleLoginView(LoginView):
    template_name = 'login.html'

    def get_success_url(self):
        return reverse('home_redirect')


class RoleLogoutView(LogoutView):
    next_page = 'login'
