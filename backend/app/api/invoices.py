from fastapi import APIRouter

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])


@router.post("/upload")
def upload_invoice():
    return {"detail": "not implemented yet"}


@router.get("/")
def list_invoices():
    return []


@router.get("/{invoice_id}")
def get_invoice(invoice_id: int):
    return {"detail": "not implemented yet"}


@router.get("/{invoice_id}/status")
def get_invoice_status(invoice_id: int):
    return {"status": "pending"}
