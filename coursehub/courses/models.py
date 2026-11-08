
from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Course(models.Model):
    title = models.CharField(max_length=200)

    subtitle = models.CharField(max_length=250, blank=True)

    description = models.TextField()

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="courses",
        null=True,
        blank=True,
    )

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    thumbnail = models.ImageField(
        upload_to="thumbnails/",
        blank=True,
    )

    is_published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

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


import re
def embed_url(url):
    m = re.search(r"(?:youtu\.be/|v=)([\w-]{11})", url)
    if m: return f"https://www.youtube.com/embed/{m.group(1)}"
    m = re.search(r"vimeo\.com/(\d+)", url)
    if m: return f"https://player.vimeo.com/video/{m.group(1)}"
    return None

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
