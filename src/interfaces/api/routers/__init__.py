"""API routers."""
from src.interfaces.api.routers.jobs import router as jobs_router
from src.interfaces.api.routers.templates import router as templates_router
from src.interfaces.api.routers.metrics_analysis import router as metrics_analysis_router
from src.interfaces.api.routers.pages import router as pages_router

__all__ = [
    "jobs_router",
    "metrics_analysis_router",
    "pages_router",
    "templates_router",
]
