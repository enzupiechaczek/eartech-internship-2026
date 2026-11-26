"""
URL configuration for healthpulse project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path


urlpatterns = [
    path('records/', include('records.urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    # Only public media (doctor profile pictures). Medical files are served
    # exclusively through the protected records download view.
    for public_dir in settings.PUBLIC_MEDIA_DIRS:
        urlpatterns += static(
            f"{settings.MEDIA_URL}{public_dir}/",
            document_root=settings.MEDIA_ROOT / public_dir,
        )
