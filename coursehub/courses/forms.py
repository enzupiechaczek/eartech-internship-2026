from django import forms

from .models import Course, Lesson, Module


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title"]


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ["title", "order"]


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["title", "notes", "video_url", "order"]
