"""URL helpers for building external-facing links."""
from fastapi import Request

from src.config import settings


def build_reports_base_url(request: Request) -> str:
    """Build Streamlit reports base URL from request."""
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()

    host = forwarded_host or (request.url.hostname or "localhost")
    if ":" in host and not host.startswith("["):
        host = host.split(":")[0]

    scheme = forwarded_proto or (request.url.scheme or "http")
    return f"{scheme}://{host}:{settings.reports_port}"
