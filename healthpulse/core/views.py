from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db.models import Q
from django.views.generic import DetailView


from appointments.models import Appointment
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
    patient = PatientProfile.objects.filter(user=request.user).first()
    appointments = Appointment.objects.none()

    if patient is not None:
        appointments = (
            Appointment.objects.filter(patient=patient)
            .select_related("doctor__user")
            .order_by("appointment_date", "time_slot")
        )

    return render(request, 'patient_dashboard.html', {'appointments': appointments})


class RoleLoginView(LoginView):
    template_name = 'login.html'

    def get_success_url(self):
        return reverse('home_redirect')


class RoleLogoutView(LogoutView):
    next_page = 'login'


# دالة دليل الأطباء - تبدأ من أول السطر تماماً وليست بداخل الكلاس
def doctor_directory(request):
    qs = DoctorProfile.objects.select_related("user")

    specialty = request.GET.get("specialty")
    name = request.GET.get("name")
    location = request.GET.get("location")

    if specialty:
        qs = qs.filter(specialty__iexact=specialty)

    if name:
        qs = qs.filter(
            Q(user__first_name__icontains=name) |
            Q(user__last_name__icontains=name) |
            Q(user__username__icontains=name)
        )

    if location:
        qs = qs.filter(clinic_branch__icontains=location)

    specialties = DoctorProfile.objects.values_list(
        "specialty", flat=True
    ).distinct()

    context = {
        "doctors": qs,
        "specialties": specialties,
        "selected_specialty": specialty or "",
        "selected_name": name or "",
        "selected_location": location or "",
    }

    return render(request, "appointments/directory.html", context)

class DoctorDetailView(DetailView):
    model = DoctorProfile
    template_name = 'appointments/doctor_detail.html'
    context_object_name = 'doctor'
