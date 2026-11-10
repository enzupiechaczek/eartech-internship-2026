from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Root: login page or the user's own dashboard
    path('', views.home_redirect, name='home'),

    # Registration
    path('register/', views.register_view, name='register'),

    # Login & Logout
    path('login/', views.RoleLoginView.as_view(), name='login'),
    path('logout/', views.RoleLogoutView.as_view(), name='logout'),

    # Role redirect + Dashboards
    path('redirect/', views.home_redirect, name='home_redirect'),
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('doctors/', views.doctor_directory, name='doctor_directory'),
    path('doctors/<int:pk>/', views.DoctorDetailView.as_view(), name='doctor_detail'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)