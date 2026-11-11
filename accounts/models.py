from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialty = models.CharField(max_length=100)
    qualifications = models.TextField()
    clinic_branch = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='doctor_profiles/', blank=True)

    def str(self):
        return self.user.get_full_name() or self.user.username