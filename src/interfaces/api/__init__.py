"""API interfaces."""
from src.interfaces.api.routers import (
    jobs_router,
    metrics_analysis_router,
    pages_router,
    templates_router,
)

__all__ = [
    "jobs_router",
    "metrics_analysis_router",
    "pages_router",
    "templates_router",
]
