from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "rating", "created_at")
    list_filter = ("rating", "course")
    search_fields = ("course__title", "student__username", "comment")


