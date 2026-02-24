"""POST /v1/route - Smart model routing endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from token_router.models import RouteRequest, RouteResponse
from token_router.router import build_route_response, route

router = APIRouter()


@router.post("/v1/route", response_model=RouteResponse)
async def route_recommendation(req: RouteRequest):
    """Analyze intent and recommend optimal model without making an API call.

    Returns model recommendations ranked by suitability,
    with estimated cost and fallback chain.
    """
    decision = route(
        messages=req.messages,
        budget_cap=req.budget_cap,
        prefer=req.prefer,
    )
    return build_route_response(decision)
