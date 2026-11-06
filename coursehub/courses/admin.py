from django.contrib import admin
from .models import Course


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "price", "is_published", "created_at")
    list_filter = ("is_published",)
    search_fields = ("title", "instructor__username")