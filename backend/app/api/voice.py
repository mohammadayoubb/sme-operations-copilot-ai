import io
import re

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
_ARABIC_SCRIPT = re.compile(r'[؀-ۿ]')

# Arabic word forms for numbers 0-9999
_ONES = [
    '', 'واحد', 'اثنان', 'ثلاثة', 'أربعة', 'خمسة', 'ستة', 'سبعة', 'ثمانية', 'تسعة',
    'عشرة', 'أحد عشر', 'اثنا عشر', 'ثلاثة عشر', 'أربعة عشر', 'خمسة عشر',
    'ستة عشر', 'سبعة عشر', 'ثمانية عشر', 'تسعة عشر',
]
_TENS     = ['', '', 'عشرون', 'ثلاثون', 'أربعون', 'خمسون', 'ستون', 'سبعون', 'ثمانون', 'تسعون']
_HUNDREDS = ['', 'مائة', 'مئتان', 'ثلاثمائة', 'أربعمائة', 'خمسمائة', 'ستمائة', 'سبعمائة', 'ثمانمائة', 'تسعمائة']


def _int_to_arabic(n: int) -> str:
    if n < 0:
        return 'سالب ' + _int_to_arabic(-n)
    if n == 0:
        return 'صفر'
    parts: list[str] = []
    if n >= 1_000_000:
        m = n // 1_000_000
        parts.append(_int_to_arabic(m) + ' مليون')
        n %= 1_000_000
    if n >= 1000:
        t = n // 1000
        if t == 1:
            parts.append('ألف')
        elif t == 2:
            parts.append('ألفان')
        elif t < 10:
            parts.append(_ONES[t] + ' آلاف')
        else:
            parts.append(_int_to_arabic(t) + ' ألف')
        n %= 1000
    if n >= 100:
        parts.append(_HUNDREDS[n // 100])
        n %= 100
    if n >= 20:
        o = n % 10
        if o:
            parts.append(_ONES[o] + ' و' + _TENS[n // 10])
        else:
            parts.append(_TENS[n // 10])
    elif n > 0:
        parts.append(_ONES[n])
    return ' '.join(parts)


def _arabicize_numbers(text: str) -> str:
    """Replace digit sequences with Arabic words when text contains Arabic script."""
    if not _ARABIC_SCRIPT.search(text):
        return text

    def _replace(m: re.Match) -> str:
        raw = m.group()
        try:
            # Handle decimals: convert each side separately
            if '.' in raw:
                integer_part, decimal_part = raw.split('.', 1)
                ar_int = _int_to_arabic(int(integer_part))
                # spell decimal digits individually
                digit_names = [_ONES[int(d)] if int(d) > 0 else 'صفر' for d in decimal_part if d.isdigit()]
                return ar_int + ' فاصلة ' + ' '.join(digit_names)
            return _int_to_arabic(int(raw))
        except (ValueError, OverflowError):
            return raw

    return re.sub(r'\b\d+(?:\.\d+)?\b', _replace, text)


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
            language="en",
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

    # Convert digits to Arabic words when text is Arabic (TTS nova mispronounces digits in Arabic)
    text = _arabicize_numbers(text)

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
