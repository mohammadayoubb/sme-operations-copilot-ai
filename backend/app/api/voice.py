import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.ai.llm import _client, complete_json
from app.ai.prompts import VOICE_COMMAND_PROMPT
from app.core.logging import get_logger
from app.security.guardrails import is_safe_input

logger = get_logger(__name__)

router = APIRouter(prefix="/api/voice", tags=["Voice"])

_ALLOWED_AUDIO = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".flac"}
_TTS_MAX_CHARS = 4096


class TranscribeResponse(BaseModel):
    transcript: str


class CommandResponse(BaseModel):
    transcript: str
    intent: str
    params: dict


class CommandRequest(BaseModel):
    transcript: str


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    import os
    ext = os.path.splitext(audio.filename or "audio.webm")[1].lower() or ".webm"
    if ext not in _ALLOWED_AUDIO:
        raise HTTPException(400, f"Unsupported audio format '{ext}'")

    data = await audio.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "Audio file exceeds 25 MB")

    # Whisper requires the file-like object to have a name attribute with extension
    audio_file = io.BytesIO(data)
    audio_file.name = f"audio{ext}"

    try:
        resp = _client().audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        transcript = resp.text.strip()
    except Exception as e:
        logger.error("voice_transcription_failed", error=str(e), ext=ext)
        raise HTTPException(502, f"Transcription failed: {str(e)}")

    logger.info("voice_transcribed", chars=len(transcript), ext=ext)
    return TranscribeResponse(transcript=transcript)


@router.post("/command", response_model=CommandResponse)
def process_voice_command(body: CommandRequest):
    transcript = body.transcript.strip()
    if not transcript:
        raise HTTPException(400, "transcript is required")

    safe, reason = is_safe_input(transcript)
    if not safe:
        raise HTTPException(400, f"Input blocked: {reason}")

    prompt = VOICE_COMMAND_PROMPT.format(transcript=transcript)
    raw = complete_json(prompt)

    import json
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {"intent": "other", "params": {}}

    intent = str(parsed.get("intent") or "other")
    params = parsed.get("params") or {}
    if not isinstance(params, dict):
        params = {}

    logger.info("voice_command_parsed", intent=intent, params_keys=list(params.keys()))
    return CommandResponse(transcript=transcript, intent=intent, params=params)


class SpeakRequest(BaseModel):
    text: str


@router.post("/speak")
def speak_text(body: SpeakRequest):
    """Convert text to speech with OpenAI TTS and return MP3 audio."""
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "text is required")

    # Truncate to model limit; trim at sentence boundary if possible
    if len(text) > _TTS_MAX_CHARS:
        text = text[:_TTS_MAX_CHARS]

    try:
        audio_response = _client().audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text,
        )
        audio_bytes = audio_response.content
    except Exception as e:
        logger.error("voice_tts_failed", error=str(e), chars=len(text))
        raise HTTPException(502, f"TTS failed: {str(e)}")

    logger.info("voice_tts_generated", chars=len(text), bytes=len(audio_bytes))
    return Response(content=audio_bytes, media_type="audio/mpeg")
