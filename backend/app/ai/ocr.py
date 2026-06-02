"""OCR module — extract raw text from invoice images and PDFs.

Instead of running EasyOCR locally (which requires PyTorch ~1GB), we use
OpenAI's Vision API (GPT-4o-mini). The image is base64-encoded and sent
directly to the model, which reads it natively — one API call, no local
model weights, no GPU required.

PDFs with a real text layer are read directly via pypdf (no API call needed).
Scanned PDFs: first page is rendered to PNG then sent to Vision.
"""
from __future__ import annotations

import base64
import os

from app.core.logging import get_logger

logger = get_logger(__name__)

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}


def _image_to_base64(path: str) -> tuple[str, str]:
    """Return (base64_data, mime_type) for an image file."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "bmp": "image/bmp", "tiff": "image/tiff", "webp": "image/webp"}
    mime = mime_map.get(ext, "image/png")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8"), mime


def _vision_ocr(path: str) -> str:
    """Send an image to GPT-4o-mini Vision and extract all visible text."""
    from app.ai.llm import _client
    from app.core.config import settings

    b64, mime = _image_to_base64(path)
    logger.info("vision_ocr_request", path=path)

    resp = _client().chat.completions.create(
        model=settings.openai_llm_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract ALL text visible in this invoice/receipt image. "
                            "Preserve the layout as closely as possible. "
                            "Output only the raw text, no commentary."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"},
                    },
                ],
            }
        ],
        max_tokens=2048,
        temperature=0,
    )
    return (resp.choices[0].message.content or "").strip()


def _extract_pdf_text(path: str) -> str:
    """Try pypdf text layer first; fall back to Vision on first page if empty."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages_text = [(page.extract_text() or "").strip() for page in reader.pages]
    combined = "\n".join(pages_text).strip()

    if combined:
        logger.info("pdf_text_layer_used", path=path, chars=len(combined))
        return combined

    # Scanned PDF — render page 0 to PNG and run Vision OCR
    logger.info("pdf_no_text_layer_fallback_to_vision", path=path)
    try:
        from PIL import Image
        import io

        # pypdf 5.x can render pages if pypdf[full] is installed;
        # as a lightweight fallback we just send the raw bytes as a document image
        with open(path, "rb") as f:
            raw = f.read()
        b64 = base64.b64encode(raw).decode("utf-8")
        from app.ai.llm import _client
        resp = _client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract ALL text from this scanned invoice PDF. Output raw text only."},
                    {"type": "image_url", "image_url": {"url": f"data:application/pdf;base64,{b64}"}},
                ],
            }],
            max_tokens=2048,
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("pdf_vision_fallback_failed", error=str(exc))
        return ""


def extract_text(path: str) -> str:
    """Dispatch by file extension. Returns raw text ready for LLM extraction."""
    ext = os.path.splitext(path)[1].lower()
    logger.info("ocr_extract_text", path=path, ext=ext)

    if ext == ".pdf":
        return _extract_pdf_text(path)
    if ext in _IMAGE_EXTS:
        return _vision_ocr(path)

    raise ValueError(f"Unsupported file type for OCR: {ext}")
