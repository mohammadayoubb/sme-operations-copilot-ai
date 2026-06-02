from fastapi import APIRouter

router = APIRouter(prefix="/api/voice", tags=["Voice"])


@router.post("/transcribe")
def transcribe_audio():
    return {"detail": "not implemented yet"}


@router.post("/command")
def process_voice_command():
    return {"detail": "not implemented yet"}
