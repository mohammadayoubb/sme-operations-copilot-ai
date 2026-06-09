from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.forecast import ProductForecast, RetrainResult
from app.services import forecasting_service

router = APIRouter(prefix="/api/forecast", tags=["Forecast"])


@router.get("/reorder", response_model=list[ProductForecast])
def get_reorder_recommendations(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return forecasting_service.get_reorder_recommendations(db, current_user.business_id)


@router.get("/stockout/{product_id}", response_model=ProductForecast)
def get_stockout_prediction(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    forecast = forecasting_service.forecast_one(db, product_id, current_user.business_id)
    if forecast is None:
        raise HTTPException(404, "Product not found")
    return forecast


@router.post("/retrain", response_model=RetrainResult)
def trigger_retraining(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        result = forecasting_service.train_and_save(db, current_user.business_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return RetrainResult(
        status="completed",
        model_name=result["model_name"],
        metrics=result["metrics"],
        trained_at=result["trained_at"],
        n_train_rows=result["n_train_rows"],
        model_path=result["model_path"],
    )
