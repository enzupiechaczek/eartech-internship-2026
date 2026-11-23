from pathlib import Path

from django.conf import settings

_CSS = Path(settings.BASE_DIR) / "static" / "css" / "healthpulse.css"


def asset_version(request):
    """Cache-buster for the theme CSS: changes whenever the file changes,
    so browsers never keep showing an old stylesheet."""
    try:
        return {"ASSET_VERSION": int(_CSS.stat().st_mtime)}
    except OSError:
        return {"ASSET_VERSION": 0}
