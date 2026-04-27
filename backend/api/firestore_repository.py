from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter

from .firebase_client import get_firestore_client

USERS_COLLECTION = "users"
PLANTS_COLLECTION = "plants"
DISEASES_COLLECTION = "diseases"
DIAGNOSES_COLLECTION = "diagnoses"
AI_LOGS_COLLECTION = "ai_logs"
REVIEWS_COLLECTION = "reviews"
COUNTERS_COLLECTION = "meta_counters"


def _to_iso8601(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _parse_firestore_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def get_user(uid: str) -> dict[str, Any] | None:
    client = get_firestore_client()
    snap = client.collection(USERS_COLLECTION).document(uid).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    return {
        "id": uid,
        "email": data.get("email", ""),
        "username": data.get("username"),
        "role": data.get("role", "user"),
        "created_at": _to_iso8601(data.get("created_at")),
    }


def upsert_user(*, uid: str, email: str, username: str | None) -> tuple[dict[str, Any], bool]:
    client = get_firestore_client()
    users = client.collection(USERS_COLLECTION)

    # Emulate SQL unique(email): no two users can own same email.
    email_owner = (
        users.where(filter=FieldFilter("email", "==", email)).limit(2).stream()
        if email
        else []
    )
    for doc in email_owner:
        if doc.id != uid:
            raise ValueError("This email is already linked to another account.")

    now = datetime.now(timezone.utc)
    ref = users.document(uid)
    snap = ref.get()
    created = not snap.exists
    payload = {
        "email": email,
        "username": username if username is not None else None,
        "role": "user" if created else (snap.to_dict() or {}).get("role", "user"),
        "updated_at": now,
    }
    if created:
        payload["created_at"] = now
        ref.set(payload)
    else:
        if username is None:
            payload.pop("username")
        ref.set(payload, merge=True)
    return get_user(uid) or {}, created


def get_plant(plant_id: int) -> dict[str, Any] | None:
    client = get_firestore_client()
    snap = client.collection(PLANTS_COLLECTION).document(str(plant_id)).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    return {
        "id": int(snap.id),
        "name_en": data.get("name_en"),
        "name_ar": data.get("name_ar"),
        "description_en": data.get("description_en"),
        "description_ar": data.get("description_ar"),
        "created_at": _to_iso8601(data.get("created_at")),
    }


def get_default_lemon_plant() -> dict[str, Any] | None:
    client = get_firestore_client()
    for snap in (
        client.collection(PLANTS_COLLECTION)
        .where(filter=FieldFilter("name_en", "==", "Lemon"))
        .limit(1)
        .stream()
    ):
        data = snap.to_dict() or {}
        return {
            "id": int(snap.id),
            "name_en": data.get("name_en"),
            "name_ar": data.get("name_ar"),
            "description_en": data.get("description_en"),
            "description_ar": data.get("description_ar"),
            "created_at": _to_iso8601(data.get("created_at")),
        }
    return None


def list_diseases_for_plant(plant_id: int) -> list[dict[str, Any]]:
    client = get_firestore_client()
    docs = client.collection(DISEASES_COLLECTION).where(
        filter=FieldFilter("plant_id", "==", plant_id)
    ).stream()
    out: list[dict[str, Any]] = []
    for snap in docs:
        data = snap.to_dict() or {}
        out.append(
            {
                "id": int(snap.id),
                "plant": int(data.get("plant_id", plant_id)),
                "name_en": data.get("name_en"),
                "name_ar": data.get("name_ar"),
                "description_en": data.get("description_en"),
                "description_ar": data.get("description_ar"),
                "causes_en": data.get("causes_en"),
                "causes_ar": data.get("causes_ar"),
                "treatment_en": data.get("treatment_en"),
                "treatment_ar": data.get("treatment_ar"),
            }
        )
    return sorted(out, key=lambda row: row["id"])


def get_disease_for_plant(plant_id: int, disease_id: int) -> dict[str, Any] | None:
    client = get_firestore_client()
    snap = client.collection(DISEASES_COLLECTION).document(str(disease_id)).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    if int(data.get("plant_id", -1)) != plant_id:
        return None
    return {
        "id": int(snap.id),
        "plant": int(data.get("plant_id")),
        "name_en": data.get("name_en"),
        "name_ar": data.get("name_ar"),
        "description_en": data.get("description_en"),
        "description_ar": data.get("description_ar"),
        "causes_en": data.get("causes_en"),
        "causes_ar": data.get("causes_ar"),
        "treatment_en": data.get("treatment_en"),
        "treatment_ar": data.get("treatment_ar"),
    }


def get_disease_by_id(disease_id: int) -> dict[str, Any] | None:
    client = get_firestore_client()
    snap = client.collection(DISEASES_COLLECTION).document(str(disease_id)).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    return {
        "id": int(snap.id),
        "plant": int(data.get("plant_id", 0) or 0),
        "name_en": data.get("name_en"),
        "name_ar": data.get("name_ar"),
        "description_en": data.get("description_en"),
        "description_ar": data.get("description_ar"),
        "causes_en": data.get("causes_en"),
        "causes_ar": data.get("causes_ar"),
        "treatment_en": data.get("treatment_en"),
        "treatment_ar": data.get("treatment_ar"),
    }


def list_all_plants() -> list[dict[str, Any]]:
    client = get_firestore_client()
    out: list[dict[str, Any]] = []
    for snap in client.collection(PLANTS_COLLECTION).stream():
        data = snap.to_dict() or {}
        out.append(
            {
                "id": int(snap.id),
                "name_en": data.get("name_en"),
                "name_ar": data.get("name_ar"),
                "description_en": data.get("description_en"),
                "description_ar": data.get("description_ar"),
                "created_at": _to_iso8601(data.get("created_at")),
            }
        )
    return sorted(out, key=lambda row: row["id"])


_DISEASE_EDITABLE_FIELDS = frozenset(
    {
        "name_en",
        "name_ar",
        "description_en",
        "description_ar",
        "causes_en",
        "causes_ar",
        "treatment_en",
        "treatment_ar",
    }
)

_PLANT_EDITABLE_FIELDS = frozenset(
    {
        "name_en",
        "name_ar",
        "description_en",
        "description_ar",
    }
)


def update_disease_fields(disease_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
    """Merge-update allowed bilingual catalog fields on a disease document."""
    patch = {k: v for k, v in fields.items() if k in _DISEASE_EDITABLE_FIELDS}
    if not patch:
        return get_disease_by_id(disease_id)
    client = get_firestore_client()
    ref = client.collection(DISEASES_COLLECTION).document(str(disease_id))
    snap = ref.get()
    if not snap.exists:
        return None
    patch["updated_at"] = datetime.now(timezone.utc)
    ref.set(patch, merge=True)
    return get_disease_by_id(disease_id)


def update_plant_fields(plant_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
    patch = {k: v for k, v in fields.items() if k in _PLANT_EDITABLE_FIELDS}
    if not patch:
        return get_plant(plant_id)
    client = get_firestore_client()
    ref = client.collection(PLANTS_COLLECTION).document(str(plant_id))
    snap = ref.get()
    if not snap.exists:
        return None
    patch["updated_at"] = datetime.now(timezone.utc)
    ref.set(patch, merge=True)
    return get_plant(plant_id)


def _next_counter_value(key: str) -> int:
    client = get_firestore_client()
    counter_ref = client.collection(COUNTERS_COLLECTION).document(key)
    transaction = client.transaction()

    @firestore.transactional
    def _allocate(txn):
        snap = counter_ref.get(transaction=txn)
        current = int((snap.to_dict() or {}).get("value", 0)) if snap.exists else 0
        nxt = current + 1
        txn.set(counter_ref, {"value": nxt}, merge=True)
        return nxt

    return int(_allocate(transaction))


def create_diagnosis_with_log(
    *,
    user_id: str,
    disease: dict[str, Any],
    input_type: str,
    image_url: str | None,
    text_input: str | None,
    confidence_score: float,
    raw_debug: str,
) -> dict[str, Any]:
    client = get_firestore_client()
    diagnosis_id = _next_counter_value("diagnoses")
    diagnosis_ref = client.collection(DIAGNOSES_COLLECTION).document(str(diagnosis_id))
    ai_log_id = _next_counter_value("ai_logs")
    ai_log_ref = client.collection(AI_LOGS_COLLECTION).document(str(ai_log_id))
    now = datetime.now(timezone.utc)
    diagnosis_doc = {
        "user_id": user_id,
        "plant_id": int(disease["plant"]),
        "disease_id": int(disease["id"]),
        "input_type": input_type,
        "image_url": image_url or None,
        "text_input": text_input or None,
        "confidence_score": float(confidence_score),
        "created_at": now,
    }
    ai_log_doc = {
        "diagnosis_id": diagnosis_id,
        "input_data": raw_debug,
        "predicted_disease": disease.get("name_en"),
        "confidence_score": float(confidence_score),
        "created_at": now,
    }
    batch = client.batch()
    batch.set(diagnosis_ref, diagnosis_doc)
    batch.set(ai_log_ref, ai_log_doc)
    batch.commit()
    return get_diagnosis_for_user(user_id=user_id, diagnosis_id=diagnosis_id) or {}


def _build_diagnosis_payload(diag_id: int, diagnosis: dict[str, Any], disease: dict[str, Any]) -> dict[str, Any]:
    disease_payload = dict(disease)
    plant_id = int(disease_payload.get("plant", 0))
    plant = get_plant(plant_id) or {}
    disease_payload["plant"] = {
        "id": plant_id,
        "name_en": plant.get("name_en"),
        "name_ar": plant.get("name_ar"),
        "description_en": plant.get("description_en"),
        "description_ar": plant.get("description_ar"),
    }
    return {
        "id": diag_id,
        "user": diagnosis.get("user_id"),
        "disease": disease_payload,
        "input_type": diagnosis.get("input_type"),
        "image_url": diagnosis.get("image_url"),
        "text_input": diagnosis.get("text_input"),
        "confidence_score": diagnosis.get("confidence_score"),
        "created_at": _to_iso8601(diagnosis.get("created_at")),
    }


def get_diagnosis_for_user(*, user_id: str, diagnosis_id: int) -> dict[str, Any] | None:
    client = get_firestore_client()
    snap = client.collection(DIAGNOSES_COLLECTION).document(str(diagnosis_id)).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    if data.get("user_id") != user_id:
        return None
    plant_id = int(data.get("plant_id", 0) or 0)
    disease_id = int(data.get("disease_id"))
    disease = get_disease_for_plant(plant_id, disease_id) if plant_id > 0 else None
    if disease is None:
        disease = get_disease_by_id(disease_id)
    if disease is None:
        return None
    return _build_diagnosis_payload(int(snap.id), data, disease)


def list_diagnoses_for_user(*, user_id: str, page: int, page_size: int) -> dict[str, Any]:
    client = get_firestore_client()
    rows: list[tuple[int, dict[str, Any]]] = []
    for snap in client.collection(DIAGNOSES_COLLECTION).where(
        filter=FieldFilter("user_id", "==", user_id)
    ).stream():
        data = snap.to_dict() or {}
        rows.append((int(snap.id), data))

    rows.sort(
        key=lambda pair: (
            _parse_firestore_time(pair[1].get("created_at")),
            pair[0],
        ),
        reverse=True,
    )

    total = len(rows)
    start = max((page - 1) * page_size, 0)
    end = start + page_size
    current = rows[start:end]
    results: list[dict[str, Any]] = []
    for diag_id, row in current:
        disease_id = int(row.get("disease_id"))
        plant_id = int(row.get("plant_id", 0) or 0)
        disease = get_disease_for_plant(plant_id, disease_id) if plant_id > 0 else None
        if disease is None:
            disease = get_disease_by_id(disease_id)
        if disease is None:
            continue
        results.append(_build_diagnosis_payload(diag_id, row, disease))

    next_page = page + 1 if end < total else None
    previous_page = page - 1 if page > 1 else None
    return {
        "count": total,
        "next": next_page,
        "previous": previous_page,
        "results": results,
    }


def seed_plant_and_diseases(*, plant: dict[str, Any], diseases: list[dict[str, Any]]) -> None:
    client = get_firestore_client()
    plant_id = int(plant["id"])
    plant_ref = client.collection(PLANTS_COLLECTION).document(str(plant_id))
    plant_doc = dict(plant)
    plant_doc.pop("id", None)
    plant_doc.setdefault("created_at", datetime.now(timezone.utc))
    plant_ref.set(plant_doc, merge=True)

    batch = client.batch()
    for disease in diseases:
        disease_id = int(disease["id"])
        dref = client.collection(DISEASES_COLLECTION).document(str(disease_id))
        doc = dict(disease)
        doc.pop("id", None)
        doc["plant_id"] = plant_id
        batch.set(dref, doc, merge=True)
    batch.commit()


def export_collection_ids(collection: str) -> list[str]:
    client = get_firestore_client()
    return [doc.id for doc in client.collection(collection).stream()]


def write_raw_document(collection: str, doc_id: str, data: dict[str, Any]) -> None:
    client = get_firestore_client()
    payload = dict(data)
    payload.setdefault("migrated_at", datetime.now(timezone.utc))
    client.collection(collection).document(doc_id).set(payload, merge=True)


def parse_json_field(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)
