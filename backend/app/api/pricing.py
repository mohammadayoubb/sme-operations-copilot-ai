from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.repositories import product_repo
from app.schemas.pricing import PriceHistoryPoint, PricingRequest, PricingResponse
from app.services import pricing_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/pricing", tags=["Pricing"])


@router.post("/analyze", response_model=PricingResponse)
def analyze_pricing(payload: PricingRequest):
    """Compute the margin in Python, then have the LLM explain it in plain language."""
    try:
        return pricing_service.analyze(payload)
    except Exception as exc:  # noqa: BLE001
        logger.error("pricing_analyze_failed", err=str(exc))
        raise HTTPException(502, f"Could not generate the explanation: {exc}")


@router.get("/history/{product_id}", response_model=list[PriceHistoryPoint])
def price_history(product_id: int, db: Session = Depends(get_db)):
    if product_repo.get_product(db, product_id) is None:
        raise HTTPException(404, "Product not found")
    return [
        PriceHistoryPoint(invoice_date=d, unit_price=p)
        for d, p in product_repo.price_history(db, product_id)
    ]
