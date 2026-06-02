from fastapi import APIRouter

router = APIRouter(prefix="/api/pricing", tags=["Pricing"])


@router.post("/analyze")
def analyze_pricing():
    return {"detail": "not implemented yet"}


@router.get("/history/{product_id}")
def price_history(product_id: int):
    return []
