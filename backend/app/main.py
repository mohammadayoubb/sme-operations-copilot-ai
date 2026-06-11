from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.logging import setup_logging
from app.api import (
    health,
    auth,
    admin,
    invoices,
    orders,
    products,
    pricing,
    forecast,
    qa,
    reports,
    voice,
    agent,
    anomaly,
    drift,
    widget,
    webhooks,
)
import app.models.widget_token  # noqa: F401 — ensures table is registered with Base

setup_logging()

app = FastAPI(
    title="SoukPilot AI",
    description="AI-first operations copilot for Lebanese SMEs",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Public routes (no JWT required) ────────────────────────────────
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(widget.router)    # own token-based auth
app.include_router(webhooks.router)  # Twilio signature validation

# ── Superadmin routes (superadmin JWT required — own dependency per route) ──
app.include_router(admin.router)

# ── Protected routes (JWT required) ────────────────────────────────
_auth = [Depends(get_current_user)]

app.include_router(invoices.router,  dependencies=_auth)
app.include_router(orders.router,    dependencies=_auth)
app.include_router(products.router,  dependencies=_auth)
app.include_router(pricing.router,   dependencies=_auth)
app.include_router(forecast.router,  dependencies=_auth)
app.include_router(qa.router,        dependencies=_auth)
app.include_router(reports.router,   dependencies=_auth)
app.include_router(voice.router,     dependencies=_auth)
app.include_router(agent.router,     dependencies=_auth)
app.include_router(anomaly.router,   dependencies=_auth)
app.include_router(drift.router,     dependencies=_auth)
