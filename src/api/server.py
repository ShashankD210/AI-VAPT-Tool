"""VAPT Tool - FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import config
from src.utils.logger import setup_logger

logger = setup_logger("vapt.api")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI-VAPT Tool API",
        description="AI-Powered Vulnerability Assessment & Penetration Testing",
        version=config.get("app.version", "3.0.0"),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get("security.cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {"status": "running", "tool": config.app_name}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app
