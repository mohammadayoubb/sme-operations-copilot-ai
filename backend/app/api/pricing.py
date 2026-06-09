from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.logging import get_logger
from app.repositories import product_repo
from app.schemas.pricing import PriceHistoryPoint, PricingRequest, PricingResponse, ProductPricingInfo
from app.services import pricing_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/pricing", tags=["Pricing"])


@router.get("/products", response_model=list[ProductPricingInfo])
def list_pricing_products(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return pricing_service.list_products_with_context(db, current_user.business_id)
    except Exception as exc:
        logger.error("pricing_products_failed", err=str(exc))
        raise HTTPException(502, f"Could not load products: {exc}")


@router.post("/analyze", response_model=PricingResponse)
def analyze_pricing(
    payload: PricingRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return pricing_service.analyze_smart(payload, db, current_user.business_id)
    except Exception as exc:
        logger.error("pricing_analyze_failed", err=str(exc))
        raise HTTPException(502, f"Could not generate the analysis: {exc}")


@router.get("/history/{product_id}", response_model=list[PriceHistoryPoint])
def price_history(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    product = product_repo.get_product(db, product_id)
    if product is None or product.business_id != current_user.business_id:
        raise HTTPException(404, "Product not found")
    return [
        PriceHistoryPoint(invoice_date=d, unit_price=p)
        for d, p in product_repo.price_history(db, product_id)
    ]
