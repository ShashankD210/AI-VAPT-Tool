"""VAPT Tool - Celery stub."""
from __future__ import annotations

from src.utils.logger import setup_logger

logger = setup_logger("vapt.celery")

celery_app = None

try:
    from celery import Celery

    celery_app = Celery("vapt", broker="redis://localhost:6379/0")
    logger.info("Celery initialized")
except ImportError:
    logger.warning("Celery not installed; running without async task queue")
