import re
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def embed_url(url):
    """Return a trusted YouTube/Vimeo embed URL, or None for unsupported links."""
    if not url:
        return None

    try:
        parsed = urlsplit(url.strip())
        host = (parsed.hostname or "").lower()
    except (AttributeError, ValueError):
        return None

    if parsed.scheme not in {"http", "https"}:
        return None

    path_parts = parsed.path.strip("/").split("/")

    if host in {"youtu.be", "www.youtu.be"}:
        video_id = path_parts[0] if path_parts else ""
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif len(path_parts) == 2 and path_parts[0] in {"embed", "shorts", "live"}:
            video_id = path_parts[1]
        else:
            video_id = ""
    elif host in {"vimeo.com", "www.vimeo.com"}:
        video_id = path_parts[0] if path_parts else ""
        if re.fullmatch(r"\d+", video_id):
            return f"https://player.vimeo.com/video/{video_id}"
        return None
    elif host == "player.vimeo.com":
        video_id = path_parts[1] if len(path_parts) == 2 and path_parts[0] == "video" else ""
        if re.fullmatch(r"\d+", video_id):
            return f"https://player.vimeo.com/video/{video_id}"
        return None
    else:
        return None

    if re.fullmatch(r"[\w-]{11}", video_id):
        return f"https://www.youtube.com/embed/{video_id}"

    return None


class Course(models.Model):
    title = models.CharField(max_length=200)

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

    def clean(self):
        super().clean()
        if self.video_url and not embed_url(self.video_url):
            raise ValidationError({
                "video_url": "Enter a valid YouTube or Vimeo video URL."
            })

    @property
    def embed(self):
        return embed_url(self.video_url)
