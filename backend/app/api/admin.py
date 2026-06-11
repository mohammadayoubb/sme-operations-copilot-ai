from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_superadmin
from app.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class TenantOut(BaseModel):
    id: int
    name: str
    created_at: Optional[str] = None
    owner_username: Optional[str] = None
    user_count: int = 0
    product_count: int = 0
    order_count: int = 0

    class Config:
        from_attributes = True


class CreateTenantRequest(BaseModel):
    business_name: str
    username: str
    password: str


class CreateTenantResponse(BaseModel):
    id: int
    name: str
    owner_username: str


@router.get("/tenants")
def list_tenants(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_superadmin),
):
    return admin_service.list_tenants(db)


@router.post("/tenants", status_code=status.HTTP_201_CREATED, response_model=CreateTenantResponse)
def create_tenant(
    payload: CreateTenantRequest,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_superadmin),
):
    return admin_service.create_tenant(db, payload.business_name, payload.username, payload.password)


@router.get("/tenants/{business_id}/stats")
def get_tenant_stats(
    business_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_superadmin),
):
    return admin_service.get_tenant_stats(db, business_id)


@router.delete("/tenants/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    business_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_superadmin),
):
    admin_service.delete_tenant(db, business_id)
