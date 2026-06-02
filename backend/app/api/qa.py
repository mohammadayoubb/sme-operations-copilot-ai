from fastapi import APIRouter

router = APIRouter(prefix="/api/qa", tags=["Q&A"])


@router.post("/ask")
def ask_question():
    return {"detail": "not implemented yet"}


@router.post("/index")
def trigger_indexing():
    return {"detail": "not implemented yet"}
