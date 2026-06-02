import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.repositories import invoice_repo, product_repo
from app.schemas.invoice import (
    InvoiceDetailOut,
    InvoiceItemOut,
    InvoiceListItem,
    InvoiceStatusResponse,
    InvoiceUploadResponse,
)

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

_ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp", ".pdf"}


@router.post("/upload", response_model=InvoiceUploadResponse, status_code=202)
async def upload_invoice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXTS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {sorted(_ALLOWED_EXTS)}")

    data = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(413, f"File exceeds {settings.max_upload_size_mb} MB limit")

    os.makedirs(settings.upload_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.upload_dir, stored_name)
    with open(file_path, "wb") as fh:
        fh.write(data)

    business = product_repo.get_or_create_default_business(db)
    invoice = invoice_repo.create_pending_invoice(db, business.id, file_path)
    db.commit()

    # Enqueue heavy OCR + extraction work
    from app.workers.invoice_tasks import process_invoice
    process_invoice.delay(invoice.id)

    return InvoiceUploadResponse(invoice_id=invoice.id, status=invoice.status)


@router.get("/", response_model=list[InvoiceListItem])
def list_invoices(db: Session = Depends(get_db)):
    return invoice_repo.list_invoices(db)


@router.get("/{invoice_id}", response_model=InvoiceDetailOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = invoice_repo.get(db, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    items = invoice_repo.get_items(db, invoice_id)
    detail = InvoiceDetailOut.model_validate(invoice)
    detail.items = [InvoiceItemOut.model_validate(i) for i in items]
    return detail


@router.get("/{invoice_id}/status", response_model=InvoiceStatusResponse)
def get_invoice_status(invoice_id: int, db: Session = Depends(get_db)):
    invoice = invoice_repo.get(db, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    return InvoiceStatusResponse(invoice_id=invoice.id, status=invoice.status)
