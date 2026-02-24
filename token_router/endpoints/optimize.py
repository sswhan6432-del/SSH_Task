"""POST /v1/optimize - Token compression endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from token_router.models import OptimizeRequest, OptimizeResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v1/optimize", response_model=OptimizeResponse)
async def optimize(req: OptimizeRequest):
    """Compress a prompt to reduce token usage.

    Levels:
      1 = Mild (10-20% reduction)
      2 = Balanced (30-50% reduction)
      3 = Aggressive (50-70% reduction)
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if req.level not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Level must be 1, 2, or 3")

    try:
        from nlp.compressor import Compressor
        compressor = Compressor()
        result = compressor.compress(req.text, level=req.level)

        return OptimizeResponse(
            original_tokens=result.original_tokens,
            compressed_tokens=result.compressed_tokens,
            reduction_rate=round(result.reduction_rate, 4),
            compressed_text=result.compressed,
            level=req.level,
        )
    except ImportError:
        logger.warning("NLP compressor module not available")
        raise HTTPException(
            status_code=503,
            detail="Compression service unavailable (NLP module not loaded)",
        )
    except Exception as e:
        logger.error("Compression failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Compression error: {e}")
