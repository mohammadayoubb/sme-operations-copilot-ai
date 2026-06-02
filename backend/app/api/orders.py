from fastapi import APIRouter

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.post("/extract")
def extract_order():
    return {"detail": "not implemented yet"}


@router.get("/")
def list_orders():
    return []


@router.patch("/{order_id}/status")
def update_order_status(order_id: int):
    return {"detail": "not implemented yet"}
