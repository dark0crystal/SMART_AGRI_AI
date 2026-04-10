"""
Pluggable lemon-tree disease prediction.

Phase 1 (stub): maps inputs to a catalog `Disease` row for the given plant.
Replace `predict_lemon_disease` with an HTTP client or local model later.
"""

from __future__ import annotations

import json
from typing import Any

from django.db.models import QuerySet

from .models import Disease, Plant

# Stub policy: use the first catalog disease ordered by pk (deterministic tests).
# Map "unknown" keyword in text to the fallback row name_en if present.


def get_default_lemon_plant() -> Plant | None:
    return Plant.objects.filter(name_en__iexact="Lemon").first()


def _diseases_for_plant(plant_id: int) -> QuerySet[Disease]:
    return Disease.objects.filter(plant_id=plant_id).order_by("id")


def predict_lemon_disease(
    *,
    plant_id: int,
    input_type: str,
    text_input: str | None,
    image_url: str | None,
) -> dict[str, Any]:
    """
    Returns keys: disease_id (int), confidence (float), raw_debug (str).
    """
    qs = _diseases_for_plant(plant_id)
    diseases = list(qs)
    if not diseases:
        raise ValueError("No diseases in catalog for this plant.")

    raw = {
        "input_type": input_type,
        "text_excerpt": (text_input or "")[:500],
        "has_image": bool(image_url),
    }

    # Prefer "Unknown" row when user hints uncertainty (stub heuristic).
    lower = (text_input or "").lower()
    unknown_row = next(
        (d for d in diseases if "unknown" in d.name_en.lower()),
        None,
    )
    if unknown_row and ("unknown" in lower or "unsure" in lower):
        chosen = unknown_row
        confidence = 0.55
    else:
        chosen = diseases[0]
        confidence = 0.82

    raw["chosen_disease"] = chosen.name_en
    raw["policy"] = "stub_v1"

    return {
        "disease_id": chosen.id,
        "confidence": confidence,
        "raw_debug": json.dumps(raw, ensure_ascii=False),
    }
