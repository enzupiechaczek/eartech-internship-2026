import re

from django.conf import settings
from django.db import models


def embed_url(url):
    if not url:
        return None

    m = re.search(r"(?:youtu\.be/|v=)([\w-]{11})", url)
    if m:
        return f"https://www.youtube.com/embed/{m.group(1)}"

    m = re.search(r"vimeo\.com/(\d+)", url)
    if m:
        return f"https://player.vimeo.com/video/{m.group(1)}"

    return None


class Course(models.Model):
    title = models.CharField(max_length=200)
    instructor = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="courses",
    )

    class Meta:
        ordering = ["title", "pk"]

    def __str__(self):
        return self.title


class Module(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules",
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return self.title


class Lesson(models.Model):
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return self.title


class Module(models.Model):
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    video_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.module.title} - {self.title}"

    @property
    def embed(self):
        return embed_url(self.video_url)
