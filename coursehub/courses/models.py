import re
from urllib.parse import urlparse

from django.conf import settings
from django.db import models


YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
VIMEO_HOSTS = {"vimeo.com", "www.vimeo.com"}


def embed_url(url):
    """Return a safe embed URL for a supported YouTube or Vimeo URL."""
    if not url:
        return None

    try:
        parsed_url = urlparse(url)
    except (TypeError, ValueError):
        return None

    if parsed_url.scheme not in {"http", "https"}:
        return None

    host = (parsed_url.hostname or "").lower()

    if host in YOUTUBE_HOSTS:
        if host == "youtu.be":
            video_id = parsed_url.path.strip("/").split("/")[0]
        else:
            video_id = parsed_urlity_query_value(parsed_url.query, "v")

        if video_id and re.fullmatch(r"[\w-]{11}", video_id):
            return f"https://www.youtube.com/embed/{video_id}"

    if host in VIMEO_HOSTS:
        match = re.match(r"^/(\d+)(?:/|$)", parsed_url.path)
        if match:
            return f"https://player.vimeo.com/video/{match.group(1)}"

    return None


def parsed_urlity_query_value(query, key):
    """Get a query-string value without accepting a URL from another host."""
    from urllib.parse import parse_qs as parse_queries

    return parse_queries(query).get(key, [None])[0]


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
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True)
    is_published = models.BooleanField(default=False)
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
