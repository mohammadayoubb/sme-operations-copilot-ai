from fastapi import APIRouter

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("/")
def list_products():
    return []


@router.get("/{product_id}")
def get_product(product_id: int):
    return {"detail": "not implemented yet"}


@router.patch("/{product_id}/stock")
def adjust_stock(product_id: int):
    return {"detail": "not implemented yet"}
