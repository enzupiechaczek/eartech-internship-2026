from urllib.parse import parse_qs, urlparse
import re

from django.conf import settings
from django.db import models


def embed_url(video_url):
    if not video_url:
        return None

    try:
        parsed = urlparse(video_url)
    except ValueError:
        return None

    host = (parsed.netloc or parsed.path).lower().replace("www.", "")
    if not host:
        return None

    if host in {"youtube.com", "m.youtube.com"} or host.endswith(".youtube.com"):
        if parsed.netloc.lower().endswith("youtu.be"):
            host = "youtu.be"
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if not video_id:
            video_id = parsed.path.strip("/").split("/embed/")[-1].split("/")[0]
        if not video_id:
            video_id = parsed.path.strip("/").split("/shorts/")[-1].split("/")[0]
        if video_id and re.fullmatch(r"[A-Za-z0-9_-]+", video_id):
            return f"https://www.youtube.com/embed/{video_id}"
        return None

    if host == "youtu.be" or host.endswith(".youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]
        if video_id and re.fullmatch(r"[A-Za-z0-9_-]+", video_id):
            return f"https://www.youtube.com/embed/{video_id}"
        return None

    if host in {"vimeo.com", "player.vimeo.com"} or host.endswith(".vimeo.com"):
        path = parsed.path.strip("/")
        if path.startswith("video/"):
            path = path.replace("video/", "", 1)
        video_id = path.split("/")[0]
        if video_id and re.fullmatch(r"\d+", video_id):
            return f"https://player.vimeo.com/video/{video_id}"
        return None

    return None


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

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='enrollments.Enrollment',
        related_name='enrolled_courses'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Module(models.Model):
    course = models.ForeignKey(
        "Course", on_delete=models.CASCADE, related_name="modules"
    )
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    video_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    @property
    def embed(self):
        return embed_url(self.video_url)

    def __str__(self):
        return f"{self.module.title} - {self.title}"
