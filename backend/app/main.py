from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.api import health, invoices, orders, products, pricing, forecast, qa, reports, voice, agent

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

app.include_router(health.router)
app.include_router(invoices.router)
app.include_router(orders.router)
app.include_router(products.router)
app.include_router(pricing.router)
app.include_router(forecast.router)
app.include_router(qa.router)
app.include_router(reports.router)
app.include_router(voice.router)
app.include_router(agent.router)
