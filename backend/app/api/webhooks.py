"""Inbound webhook handlers.

WhatsApp (Twilio):
  Twilio POSTs form-encoded data to POST /api/webhooks/whatsapp whenever a
  message arrives on the sandbox / production number.

  Signature validation uses HMAC-SHA1 against TWILIO_AUTH_TOKEN.  If the env
  var is not set the check is skipped (safe for local dev / demo; lock it down
  in production).

  Responds with TwiML XML so Twilio can send a reply back to the sender.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Optional

from fastapi import APIRouter, Form, Header, HTTPException, Request, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.repositories import order_repo
from app.services.order_service import GuardrailError, extract_and_create_order

logger = get_logger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


# ── Twilio signature validation ──────────────────────────────────────────────

def _validate_twilio_signature(
    auth_token: str,
    signature: str,
    url: str,
    params: dict[str, str],
) -> bool:
    """Validate the X-Twilio-Signature header.

    Algorithm: concatenate sorted key+value pairs to the URL, sign with
    HMAC-SHA1 using the auth token, compare base64 digest.
    """
    s = url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    mac = hmac.new(auth_token.encode("utf-8"), s.encode("utf-8"), hashlib.sha1)
    expected = base64.b64encode(mac.digest()).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _twiml_message(body: str) -> Response:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Message>{body}</Message>"
        "</Response>"
    )
    return Response(content=xml, media_type="application/xml")


# ── WhatsApp webhook ─────────────────────────────────────────────────────────

@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
    # Twilio posts these form fields
    From: Optional[str] = Form(None),
    Body: Optional[str] = Form(None),
    x_twilio_signature: Optional[str] = Header(None, alias="X-Twilio-Signature"),
):
    """Receive an inbound WhatsApp message from Twilio and extract an order.

    Twilio expects a 200 TwiML response within ~15 seconds.
    """
    # --- Signature validation (skipped in dev when auth token is not configured) ---
    if settings.twilio_auth_token:
        if not x_twilio_signature:
            raise HTTPException(403, "Missing X-Twilio-Signature")
        form_data = await request.form()
        params = {k: v for k, v in form_data.items()}
        url = str(request.url)
        if not _validate_twilio_signature(
            settings.twilio_auth_token, x_twilio_signature, url, params
        ):
            logger.warning("twilio_signature_invalid", url=url)
            raise HTTPException(403, "Invalid Twilio signature")

    message_text = (Body or "").strip()
    sender = (From or "unknown").replace("whatsapp:", "")

    if not message_text:
        return _twiml_message("Hello! Send us your order and we'll process it right away.")

    logger.info("whatsapp_inbound", from_number=sender, body_len=len(message_text))

    try:
        order = extract_and_create_order(db, message_text, source="whatsapp")
        db.commit()

        intent = (order.extracted_json or {}).get("intent", "unknown")
        confidence = order.confidence_score or 1.0
        review_status = order.review_status or "auto_approved"

        if intent == "new_order":
            items = order_repo.get_items(db, order.id)
            if items:
                item_lines = ", ".join(
                    f"{i.quantity}x {i.product_name}" for i in items[:3]
                )
                if len(items) > 3:
                    item_lines += f" (+{len(items) - 3} more)"
            else:
                item_lines = "items"

            if review_status == "needs_review":
                pct = int(confidence * 100)
                reply = (
                    f"Got your order! It's been flagged for a quick review "
                    f"(confidence: {pct}%) — we'll confirm shortly. "
                    f"Items: {item_lines}."
                )
            else:
                reply = (
                    f"Order #{order.id} confirmed! "
                    f"Items: {item_lines}. "
                    f"Delivery: {order.delivery_area or 'TBD'}. "
                    f"Payment: {order.payment_method or 'TBD'}. Thank you!"
                )
        elif intent == "inquiry":
            reply = "Thanks for your message! A team member will get back to you shortly."
        elif intent == "complaint":
            reply = "We're sorry to hear that. A team member will follow up with you shortly."
        else:
            reply = "Thanks for reaching out! How can we help you today?"

    except GuardrailError:
        reply = "Sorry, we couldn't process that message. Please send a clear order."
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("whatsapp_order_failed", err=str(exc))
        reply = "Sorry, something went wrong processing your message. Please try again."

    return _twiml_message(reply)
