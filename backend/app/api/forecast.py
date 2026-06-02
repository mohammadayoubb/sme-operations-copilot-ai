from fastapi import APIRouter

router = APIRouter(prefix="/api/forecast", tags=["Forecast"])


@router.get("/reorder")
def get_reorder_recommendations():
    return []


@router.get("/stockout/{product_id}")
def get_stockout_prediction(product_id: int):
    return {"detail": "not implemented yet"}


@router.post("/retrain")
def trigger_retraining():
    return {"detail": "not implemented yet"}
