"""
Lemon leaf disease prediction: vision uses PyTorch checkpoint; text uses TF-IDF cosine similarity.
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any

from django.conf import settings
from PIL import Image

from .firestore_repository import get_default_lemon_plant, list_diseases_for_plant

logger = logging.getLogger(__name__)


class VisionDependenciesMissing(Exception):
    """torch / torchvision / timm not installed (needed for image diagnosis)."""


_vision_bundle: tuple[Any, list[str], Any] | None = None
_text_bundle: tuple[Any, Any, list[str]] | None = None


def _diseases_for_plant(plant_id: int) -> list[dict[str, Any]]:
    return list_diseases_for_plant(plant_id)


def _get_vision_bundle():
    global _vision_bundle
    if _vision_bundle is None:
        try:
            import torch
        except ImportError as exc:
            raise VisionDependenciesMissing(
                "PyTorch is not installed. From backend/: pip install -r requirements.txt "
                "(includes torch, torchvision, timm)."
            ) from exc
        try:
            from vision.checkpoint import load_checkpoint
        except ImportError as exc:
            raise VisionDependenciesMissing(
                "Vision packages failed to import. From backend/: pip install -r requirements.txt "
                "(includes torch, torchvision, timm)."
            ) from exc

        path = Path(settings.VISION_MODEL_PATH)
        if not path.exists():
            raise ValueError(f"Vision model file not found: {path}")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_name = getattr(settings, "VISION_MODEL_NAME", "efficientnet_b1")
        try:
            model, class_names = load_checkpoint(
                path,
                device,
                default_model_name=model_name,
            )
        except ImportError as exc:
            raise VisionDependenciesMissing(
                "timm or torchvision is missing. From backend/: pip install -r requirements.txt"
            ) from exc
        _maybe_warn_missing_catalog(class_names)
        _vision_bundle = (model, class_names, device)
    return _vision_bundle


def _maybe_warn_missing_catalog(class_names: list[str]) -> None:
    lemon = get_default_lemon_plant()
    if not lemon:
        return
    known = set(
        row["name_en"] for row in list_diseases_for_plant(int(lemon["id"]))
    )
    unknown_label = settings.VISION_UNKNOWN_DISEASE_NAME_EN
    for cn in class_names:
        if cn not in known:
            logger.warning(
                "Checkpoint class %r has no matching Disease.name_en for Lemon; "
                "run migrations.",
                cn,
            )
    if unknown_label not in known:
        logger.warning(
            "Fallback disease %r missing from catalog for Lemon.",
            unknown_label,
        )


def _get_text_bundle():
    global _text_bundle
    if _text_bundle is None:
        from text.predict import load_text_model

        path = Path(settings.TEXT_MODEL_PATH)
        if not path.is_dir():
            raise ValueError(f"Text model folder not found: {path}")
        vectorizer, class_matrix, class_names = load_text_model(path)
        _text_bundle = (vectorizer, class_matrix, class_names)
    return _text_bundle


def _download_image(url: str, max_bytes: int, timeout: int) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SmartAgriAI/1.0"},
        method="GET",
    )
    ssl_context = None
    try:
        import certifi

        ssl_context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        # Fallback to default trust store when certifi is unavailable.
        ssl_context = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(
                        f"Image exceeds maximum size ({max_bytes} bytes).",
                    )
                chunks.append(chunk)
    except urllib.error.URLError as exc:
        raise ValueError(f"Could not download image URL: {exc.reason}") from exc

    return b"".join(chunks)


def _resolve_disease_for_label(
    *,
    label: str,
    diseases_by_name: dict[str, dict[str, Any]],
    unknown: dict[str, Any],
) -> dict[str, Any]:
    d = diseases_by_name.get(label)
    if d is not None:
        return d
    logger.warning("Predicted label %r not in catalog; using unknown row.", label)
    return unknown


def _apply_witch_broom_guard(
    *,
    predicted_label: str,
    top_k: list[dict[str, Any]],
) -> tuple[str, dict[str, Any] | None]:
    """
    Mitigate a known false-positive pattern where Witch's Broom wins with uncertain scores.

    Rule:
    - top-1 label is Witch's Broom
    - top-1 and top-2 probability difference is <= configured max diff (35% by default)
    In this case, choose top-2 label instead.
    """
    witch_label = settings.VISION_WITCH_BROOM_LABEL
    max_diff = settings.VISION_WITCH_BROOM_MAX_DIFF

    if predicted_label != witch_label or len(top_k) < 2:
        return predicted_label, None

    first = top_k[0]
    second = top_k[1]
    first_prob = float(first.get("prob", 0.0))
    second_prob = float(second.get("prob", 0.0))
    gap = abs(first_prob - second_prob)

    if gap <= max_diff:
        second_label = str(second.get("name", predicted_label))
        decision = {
            "applied": True,
            "reason": "witch_broom_diff_below_threshold",
            "from_label": predicted_label,
            "to_label": second_label,
            "first_prob": first_prob,
            "second_prob": second_prob,
            "gap": gap,
            "max_diff": max_diff,
        }
        return second_label, decision

    return predicted_label, {
        "applied": False,
        "reason": "gap_above_threshold",
        "label": predicted_label,
        "first_prob": first_prob,
        "second_prob": second_prob,
        "gap": gap,
        "max_diff": max_diff,
    }


def _log_image_inference(
    *,
    out: dict[str, Any],
    chosen_label: str,
    model_top_label: str,
    guard_decision: dict[str, Any] | None,
) -> None:
    if not getattr(settings, "VISION_LOG_CLASS_PROBS", True):
        return

    top_k = out.get("top_k", [])
    probs_str = ", ".join(
        f"{row.get('name')}={float(row.get('prob', 0.0)):.4f}"
        for row in top_k
    )
    logger.warning(
        "Vision probs: [%s] | model_top=%s | chosen=%s | guard=%s",
        probs_str,
        model_top_label,
        chosen_label,
        guard_decision,
    )


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

    diseases_by_name = {d["name_en"]: d for d in diseases}
    unknown_label = settings.VISION_UNKNOWN_DISEASE_NAME_EN
    unknown_row = diseases_by_name.get(unknown_label)
    if unknown_row is None:
        unknown_row = next(
            (d for d in diseases if "unknown" in d["name_en"].lower()),
            diseases[0],
        )

    if input_type == "image":
        return _predict_image(
            image_url=image_url or "",
            diseases_by_name=diseases_by_name,
            unknown_row=unknown_row,
        )

    return _predict_text(
        text_input=text_input,
        diseases_by_name=diseases_by_name,
        unknown_row=unknown_row,
    )


def _predict_image(
    *,
    image_url: str,
    diseases_by_name: dict[str, dict[str, Any]],
    unknown_row: dict[str, Any],
) -> dict[str, Any]:
    from vision.predict import predict_from_pil

    model, class_names, device = _get_vision_bundle()
    raw_bytes = _download_image(
        image_url,
        settings.VISION_IMAGE_MAX_BYTES,
        settings.VISION_IMAGE_DOWNLOAD_TIMEOUT,
    )
    image = Image.open(BytesIO(raw_bytes))
    out = predict_from_pil(model, class_names, device, image, top_k=5)

    model_top_label = out["predicted_label"]
    label = model_top_label
    guard_label, guard_decision = _apply_witch_broom_guard(
        predicted_label=label,
        top_k=out["top_k"],
    )
    if guard_label != label:
        label = guard_label
    top_prob = float(out["confidence"])
    min_conf = settings.VISION_MIN_CONFIDENCE

    if top_prob < min_conf:
        chosen = unknown_row
        raw = {
            "input_type": "image",
            "policy": "vision_checkpoint",
            "below_min_confidence": True,
            "min_confidence": min_conf,
            "model_top_label": model_top_label,
            "effective_label": label,
            "model_top_prob": top_prob,
            "top_k": out["top_k"],
            "witch_broom_guard": guard_decision,
        }
    else:
        chosen = _resolve_disease_for_label(
            label=label,
            diseases_by_name=diseases_by_name,
            unknown=unknown_row,
        )
        raw = {
            "input_type": "image",
            "policy": "vision_checkpoint",
            "below_min_confidence": False,
            "min_confidence": min_conf,
            "chosen_disease": chosen["name_en"],
            "chosen_disease": chosen["name_en"],
            "top_k": out["top_k"],
            "witch_broom_guard": guard_decision,
        }

    _log_image_inference(
        out=out,
        chosen_label=chosen["name_en"],
        model_top_label=model_top_label,
        guard_decision=guard_decision,
    )

    return {
        "disease_id": int(chosen["id"]),
        "confidence": top_prob,
        "raw_debug": json.dumps(raw, ensure_ascii=False),
    }


def predict_lemon_uploaded_image(
    *,
    image_bytes: bytes,
    plant_id: int | None = None,
) -> dict[str, Any]:
    """
    Run image inference directly from uploaded bytes (debug UI helper).
    Returns disease_id, confidence, raw_debug, chosen_disease.
    """
    if plant_id is None:
        lemon = get_default_lemon_plant()
        if not lemon:
            raise ValueError("Lemon catalog is not seeded. Run migrations.")
        plant_id = int(lemon["id"])

    diseases = list(_diseases_for_plant(plant_id))
    if not diseases:
        raise ValueError("No diseases in catalog for this plant.")

    diseases_by_name = {d["name_en"]: d for d in diseases}
    unknown_label = settings.VISION_UNKNOWN_DISEASE_NAME_EN
    unknown_row = diseases_by_name.get(unknown_label)
    if unknown_row is None:
        unknown_row = next(
            (d for d in diseases if "unknown" in d["name_en"].lower()),
            diseases[0],
        )

    from vision.predict import predict_from_pil

    model, class_names, device = _get_vision_bundle()
    image = Image.open(BytesIO(image_bytes))
    out = predict_from_pil(model, class_names, device, image, top_k=5)

    model_top_label = out["predicted_label"]
    label = model_top_label
    guard_label, guard_decision = _apply_witch_broom_guard(
        predicted_label=label,
        top_k=out["top_k"],
    )
    if guard_label != label:
        label = guard_label
    top_prob = float(out["confidence"])
    min_conf = settings.VISION_MIN_CONFIDENCE

    if top_prob < min_conf:
        chosen = unknown_row
        raw = {
            "input_type": "image",
            "policy": "vision_checkpoint",
            "below_min_confidence": True,
            "min_confidence": min_conf,
            "model_top_label": model_top_label,
            "effective_label": label,
            "model_top_prob": top_prob,
            "top_k": out["top_k"],
            "witch_broom_guard": guard_decision,
        }
    else:
        chosen = _resolve_disease_for_label(
            label=label,
            diseases_by_name=diseases_by_name,
            unknown=unknown_row,
        )
        raw = {
            "input_type": "image",
            "policy": "vision_checkpoint",
            "below_min_confidence": False,
            "min_confidence": min_conf,
            "chosen_disease": chosen["name_en"],
            "top_k": out["top_k"],
            "witch_broom_guard": guard_decision,
        }

    _log_image_inference(
        out=out,
        chosen_label=chosen["name_en"],
        model_top_label=model_top_label,
        guard_decision=guard_decision,
    )

    return {
        "disease_id": int(chosen["id"]),
        "chosen_disease": chosen["name_en"],
        "confidence": top_prob,
        "raw_debug": json.dumps(raw, ensure_ascii=False),
    }


def _predict_text(
    *,
    text_input: str | None,
    diseases_by_name: dict[str, dict[str, Any]],
    unknown_row: dict[str, Any],
) -> dict[str, Any]:
    from text.predict import predict_from_text

    vectorizer, class_matrix, class_names = _get_text_bundle()
    out = predict_from_text(text_input or "", vectorizer, class_matrix, class_names)

    label = out["predicted_label"]
    confidence = float(out["confidence"])
    min_conf = settings.TEXT_MIN_CONFIDENCE

    if confidence < min_conf:
        chosen = unknown_row
        raw = {
            "input_type": "text",
            "text_excerpt": (text_input or "")[:500],
            "policy": "tfidf_v1",
            "below_min_confidence": True,
            "min_confidence": min_conf,
            "model_top_label": label,
            "model_top_score": confidence,
            "all_scores": out["all_scores"],
        }
    else:
        chosen = _resolve_disease_for_label(
            label=label,
            diseases_by_name=diseases_by_name,
            unknown=unknown_row,
        )
        raw = {
            "input_type": "text",
            "text_excerpt": (text_input or "")[:500],
            "policy": "tfidf_v1",
            "below_min_confidence": False,
            "min_confidence": min_conf,
            "chosen_disease": chosen["name_en"],
            "model_top_label": label,
            "model_top_score": confidence,
            "all_scores": out["all_scores"],
        }

    return {
        "disease_id": int(chosen["id"]),
        "confidence": confidence,
        "raw_debug": json.dumps(raw, ensure_ascii=False),
    }
