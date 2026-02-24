"""GET /v1/stats - Usage statistics endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from token_router.models import StatsResponse

router = APIRouter()


@router.get("/v1/stats", response_model=StatsResponse)
async def get_stats():
    """Return usage statistics."""
    from token_router.endpoints.chat import get_stats as _get_stats

    data = _get_stats()
    total_req = data["total_requests"] or 1

    return StatsResponse(
        total_requests=data["total_requests"],
        total_tokens=data["total_tokens"],
        total_cost_usd=round(data["total_cost_usd"], 6),
        total_savings_usd=round(data["total_savings_usd"], 6),
        cache_hit_rate=0.0,
        requests_by_provider=data["requests_by_provider"],
        requests_by_model=data["requests_by_model"],
        avg_latency_ms=round(data["latency_sum_ms"] / total_req, 1),
    )


@router.get("/dashboard")
async def dashboard():
    """Serve the dashboard HTML page."""
    import os
    dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    return FileResponse(dashboard_path, media_type="text/html")


@router.get("/dashboard/{filename}")
async def dashboard_static(filename: str):
    """Serve dashboard static files."""
    import os
    dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard")
    filepath = os.path.join(dashboard_dir, filename)
    if not os.path.isfile(filepath):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    ext_map = {".js": "application/javascript", ".css": "text/css", ".html": "text/html"}
    ext = os.path.splitext(filename)[1]
    return FileResponse(filepath, media_type=ext_map.get(ext, "application/octet-stream"))
