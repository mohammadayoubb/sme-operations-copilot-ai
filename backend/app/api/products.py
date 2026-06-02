from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import product_repo
from app.schemas.product import ProductOut

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("/", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return product_repo.list_products(db)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = product_repo.get_product(db, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product
