"""Pantheon API gateway entrypoint."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pantheon_api.db import dispose_engine, init_engine
from pantheon_api.logging import configure_logging
from pantheon_api.routers import (
    adversarial,
    agents,
    arc,
    auth,
    counterfactual,
    debates,
    elysium,
    goals,
    health,
    markets,
    moirai,
    olympus,
    passports,
    restraint,
    signals,
    theses,
    traces,
    trades,
    underworld,
)

log = structlog.get_logger("pantheon_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_engine()
    log.info("pantheon_api.startup")
    try:
        yield
    finally:
        await dispose_engine()
        log.info("pantheon_api.shutdown")


app = FastAPI(
    title="Pantheon Trades API",
    version="0.1.0",
    description="AI-powered prediction market trading council",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(signals.router, prefix="/signals", tags=["signals"])
app.include_router(theses.router, prefix="/theses", tags=["theses"])
app.include_router(debates.router, prefix="/debates", tags=["debates"])
app.include_router(traces.router, prefix="/traces", tags=["traces"])
app.include_router(trades.router, prefix="/trades", tags=["trades"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(passports.router, prefix="/passports", tags=["passports"])
app.include_router(markets.router, prefix="/markets", tags=["markets"])
app.include_router(goals.router, prefix="/goals", tags=["goals"])
app.include_router(olympus.router, prefix="/olympus", tags=["olympus"])
app.include_router(moirai.router, prefix="/moirai", tags=["moirai"])
app.include_router(elysium.router, prefix="/elysium", tags=["elysium"])
app.include_router(restraint.router, prefix="/restraint", tags=["restraint"])
app.include_router(adversarial.router, prefix="/adversarial", tags=["adversarial"])
app.include_router(counterfactual.router, prefix="/counterfactuals", tags=["counterfactuals"])
app.include_router(underworld.router, prefix="/underworld", tags=["underworld"])
app.include_router(arc.router, prefix="/arc", tags=["arc"])
