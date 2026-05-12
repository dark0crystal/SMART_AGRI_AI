from __future__ import annotations

import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)

# `ready()` is invoked for every management command (migrate, seed, shell, ...).
# Only warm the (heavy) ML models when running an actual server, never for
# short-lived utility commands.
_SERVER_LIKE_COMMANDS = {"runserver", "uvicorn", "gunicorn", "daphne"}


def _is_server_invocation() -> bool:
    if os.environ.get("RUN_MAIN") == "true":
        return True
    if not sys.argv:
        return True
    if len(sys.argv) <= 1:
        return True
    cmd = os.path.basename(sys.argv[0]).lower()
    if cmd in {"gunicorn", "uvicorn", "daphne"}:
        return True
    if "manage.py" in cmd or cmd == "manage.py":
        return sys.argv[1] in _SERVER_LIKE_COMMANDS
    return False


def _warm_models() -> None:
    """Force-load the vision + text bundles and run a single warm forward pass."""
    from .ai_service import _get_text_bundle, _get_vision_bundle

    try:
        model, _class_names, device = _get_vision_bundle()
    except Exception:
        logger.exception("Vision warmup: failed to load bundle")
        return
    try:
        import torch

        with torch.no_grad():
            model(torch.zeros(1, 3, 224, 224, device=device))
    except Exception:
        logger.exception("Vision warmup: forward pass failed")

    try:
        _get_text_bundle()
    except Exception:
        logger.exception("Text warmup: failed to load bundle")


class ApiConfig(AppConfig):
    name = "api"

    def ready(self) -> None:
        from django.conf import settings

        if not getattr(settings, "AI_WARMUP_ON_START", True):
            return
        if not _is_server_invocation():
            return
        # Run inline; called once at process start, not in the request hot path.
        _warm_models()
