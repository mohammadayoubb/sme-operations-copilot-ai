from fastapi import APIRouter

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/")
def list_reports():
    return []


@router.get("/latest")
def get_latest_report():
    return {"detail": "not implemented yet"}


@router.post("/generate")
def generate_report():
    return {"detail": "not implemented yet"}
