from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.core.cache import cache
from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter

from .firebase_client import get_firestore_client

logger = logging.getLogger(__name__)

USERS_COLLECTION = "users"
PLANTS_COLLECTION = "plants"
DISEASES_COLLECTION = "diseases"
DIAGNOSES_COLLECTION = "diagnoses"
AI_LOGS_COLLECTION = "ai_logs"
REVIEWS_COLLECTION = "reviews"
COUNTERS_COLLECTION = "meta_counters"

# Cache key namespaces. Keep them short and stable across processes.
_USER_CACHE_KEY = "fs:user:{uid}"
_PLANT_CACHE_KEY = "fs:plant:{pid}"
_PLANTS_ALL_CACHE_KEY = "fs:plants:all"
_DEFAULT_LEMON_CACHE_KEY = "fs:plants:default_lemon"
_DISEASE_CACHE_KEY = "fs:disease:{did}"
_DISEASES_FOR_PLANT_CACHE_KEY = "fs:diseases:plant:{pid}"
# Sentinel for cached "missing" values so we don't re-query Firestore for known absent keys.
_MISSING = "__missing__"


def _user_ttl() -> int:
    return int(getattr(settings, "USER_CACHE_TTL", 60))


def _catalog_ttl() -> int:
    return int(getattr(settings, "CATALOG_CACHE_TTL", 300))


def _cache_set(key: str, value: Any, ttl: int) -> None:
    """Cache a value, using a sentinel for ``None`` so we can distinguish miss vs absent."""
    cache.set(key, value if value is not None else _MISSING, ttl)


def _invalidate_user(uid: str) -> None:
    cache.delete(_USER_CACHE_KEY.format(uid=uid))


def _invalidate_plant(plant_id: int | None = None) -> None:
    cache.delete(_PLANTS_ALL_CACHE_KEY)
    cache.delete(_DEFAULT_LEMON_CACHE_KEY)
    if plant_id is not None:
        cache.delete(_PLANT_CACHE_KEY.format(pid=int(plant_id)))
        cache.delete(_DISEASES_FOR_PLANT_CACHE_KEY.format(pid=int(plant_id)))


def _invalidate_disease(disease_id: int, plant_id: int | None = None) -> None:
    cache.delete(_DISEASE_CACHE_KEY.format(did=int(disease_id)))
    if plant_id is not None:
        cache.delete(_DISEASES_FOR_PLANT_CACHE_KEY.format(pid=int(plant_id)))


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


def _fetch_user(uid: str) -> dict[str, Any] | None:
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


def get_user(uid: str) -> dict[str, Any] | None:
    key = _USER_CACHE_KEY.format(uid=uid)
    cached = cache.get(key)
    if cached is _MISSING:
        return None
    if cached is not None:
        return cached
    user = _fetch_user(uid)
    _cache_set(key, user, _user_ttl())
    return user


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
    _invalidate_user(uid)
    return _fetch_user(uid) or {}, created


def _fetch_plant(plant_id: int) -> dict[str, Any] | None:
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


def get_plant(plant_id: int) -> dict[str, Any] | None:
    key = _PLANT_CACHE_KEY.format(pid=int(plant_id))
    cached = cache.get(key)
    if cached is _MISSING:
        return None
    if cached is not None:
        return cached
    plant = _fetch_plant(plant_id)
    _cache_set(key, plant, _catalog_ttl())
    return plant


def _fetch_default_lemon_plant() -> dict[str, Any] | None:
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


def get_default_lemon_plant() -> dict[str, Any] | None:
    cached = cache.get(_DEFAULT_LEMON_CACHE_KEY)
    if cached is _MISSING:
        return None
    if cached is not None:
        return cached
    plant = _fetch_default_lemon_plant()
    _cache_set(_DEFAULT_LEMON_CACHE_KEY, plant, _catalog_ttl())
    return plant


def _fetch_diseases_for_plant(plant_id: int) -> list[dict[str, Any]]:
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


def list_diseases_for_plant(plant_id: int) -> list[dict[str, Any]]:
    key = _DISEASES_FOR_PLANT_CACHE_KEY.format(pid=int(plant_id))
    cached = cache.get(key)
    if cached is _MISSING:
        return []
    if cached is not None:
        return list(cached)
    rows = _fetch_diseases_for_plant(plant_id)
    # Always cache (use empty list as a real value, not the missing sentinel).
    cache.set(key, rows, _catalog_ttl())
    return rows


def _fetch_disease_by_id(disease_id: int) -> dict[str, Any] | None:
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


def get_disease_by_id(disease_id: int) -> dict[str, Any] | None:
    key = _DISEASE_CACHE_KEY.format(did=int(disease_id))
    cached = cache.get(key)
    if cached is _MISSING:
        return None
    if cached is not None:
        return cached
    disease = _fetch_disease_by_id(disease_id)
    _cache_set(key, disease, _catalog_ttl())
    return disease


def get_disease_for_plant(plant_id: int, disease_id: int) -> dict[str, Any] | None:
    """Return the disease only if it belongs to the requested plant."""
    disease = get_disease_by_id(disease_id)
    if disease is None:
        return None
    try:
        if int(disease.get("plant", -1)) != int(plant_id):
            return None
    except (TypeError, ValueError):
        return None
    return disease


def list_all_plants() -> list[dict[str, Any]]:
    cached = cache.get(_PLANTS_ALL_CACHE_KEY)
    if cached is _MISSING:
        return []
    if cached is not None:
        return list(cached)
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
    rows = sorted(out, key=lambda row: row["id"])
    cache.set(_PLANTS_ALL_CACHE_KEY, rows, _catalog_ttl())
    return rows


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
    plant_id = None
    try:
        plant_id = int((snap.to_dict() or {}).get("plant_id", 0) or 0) or None
    except (TypeError, ValueError):
        plant_id = None
    _invalidate_disease(disease_id, plant_id)
    return _fetch_disease_by_id(disease_id)


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
    _invalidate_plant(plant_id)
    return _fetch_plant(plant_id)


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


def _build_diagnosis_payload_prefetched(
    diag_id: int,
    diagnosis: dict[str, Any],
    disease: dict[str, Any],
    plants_by_id: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Same shape as _build_diagnosis_payload, but uses a prefetched plant map."""
    disease_payload = dict(disease)
    try:
        plant_id = int(disease_payload.get("plant", 0) or 0)
    except (TypeError, ValueError):
        plant_id = 0
    plant = plants_by_id.get(plant_id, {})
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


def list_diagnoses_for_user(*, user_id: str, page: int, page_size: int) -> dict[str, Any]:
    """
    Paginated list of diagnoses for a user.

    Optimisations vs. the naive version:
    - Prefer Firestore-side ordering with offset+limit (one round-trip for the page).
      Requires the composite index ``user_id ASC + created_at DESC`` on ``diagnoses``;
      if Firestore reports the index missing we transparently fall back to the legacy
      in-memory sort so behaviour is preserved.
    - Bulk-prefetches the diseases and plants referenced by the page in two
      ``client.get_all`` round-trips, eliminating the previous N+1 lookups.

    Response shape is unchanged: ``{count, next, previous, results}``.
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1

    client = get_firestore_client()
    base_query = client.collection(DIAGNOSES_COLLECTION).where(
        filter=FieldFilter("user_id", "==", user_id)
    )
    offset_count = (page - 1) * page_size

    page_rows: list[tuple[int, dict[str, Any]]] = []
    total: int | None = None
    server_ordered = False

    try:
        ordered_query = base_query.order_by(
            "created_at", direction=firestore.Query.DESCENDING
        )
        if offset_count:
            ordered_query = ordered_query.offset(offset_count)
        ordered_query = ordered_query.limit(page_size + 1)
        for snap in ordered_query.stream():
            try:
                page_rows.append((int(snap.id), snap.to_dict() or {}))
            except (TypeError, ValueError):
                continue
        server_ordered = True
    except Exception as exc:
        logger.warning(
            "list_diagnoses_for_user: server-side ordering failed (%s); "
            "falling back to in-memory sort. Create composite Firestore index "
            "user_id ASC + created_at DESC on collection 'diagnoses' to speed this up.",
            exc,
        )

    if not server_ordered:
        all_rows: list[tuple[int, dict[str, Any]]] = []
        for snap in base_query.stream():
            try:
                all_rows.append((int(snap.id), snap.to_dict() or {}))
            except (TypeError, ValueError):
                continue
        all_rows.sort(
            key=lambda pair: (
                _parse_firestore_time(pair[1].get("created_at")),
                pair[0],
            ),
            reverse=True,
        )
        total = len(all_rows)
        page_rows = all_rows[offset_count : offset_count + page_size + 1]

    has_next = len(page_rows) > page_size
    if has_next:
        page_rows = page_rows[:page_size]

    if total is None:
        try:
            agg_result = base_query.count().get()
            total = int(agg_result[0][0].value)
        except Exception:
            total = None

    disease_ids: list[int] = []
    seen_disease_ids: set[int] = set()
    for _diag_id, data in page_rows:
        try:
            did = int(data.get("disease_id"))
        except (TypeError, ValueError):
            continue
        if did in seen_disease_ids:
            continue
        seen_disease_ids.add(did)
        disease_ids.append(did)

    diseases_by_id: dict[int, dict[str, Any]] = {}
    if disease_ids:
        disease_refs = [
            client.collection(DISEASES_COLLECTION).document(str(did))
            for did in disease_ids
        ]
        for snap in client.get_all(disease_refs):
            if not snap.exists:
                continue
            try:
                snap_id = int(snap.id)
            except (TypeError, ValueError):
                continue
            data = snap.to_dict() or {}
            diseases_by_id[snap_id] = {
                "id": snap_id,
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

    plant_ids: set[int] = set()
    for _diag_id, data in page_rows:
        try:
            pid = int(data.get("plant_id", 0) or 0)
            if pid > 0:
                plant_ids.add(pid)
        except (TypeError, ValueError):
            pass
    for d in diseases_by_id.values():
        try:
            pid = int(d.get("plant", 0) or 0)
            if pid > 0:
                plant_ids.add(pid)
        except (TypeError, ValueError):
            pass

    plants_by_id: dict[int, dict[str, Any]] = {}
    if plant_ids:
        plant_refs = [
            client.collection(PLANTS_COLLECTION).document(str(pid))
            for pid in plant_ids
        ]
        for snap in client.get_all(plant_refs):
            if not snap.exists:
                continue
            try:
                snap_id = int(snap.id)
            except (TypeError, ValueError):
                continue
            data = snap.to_dict() or {}
            plants_by_id[snap_id] = {
                "id": snap_id,
                "name_en": data.get("name_en"),
                "name_ar": data.get("name_ar"),
                "description_en": data.get("description_en"),
                "description_ar": data.get("description_ar"),
                "created_at": _to_iso8601(data.get("created_at")),
            }

    results: list[dict[str, Any]] = []
    for diag_id, data in page_rows:
        try:
            did = int(data.get("disease_id"))
        except (TypeError, ValueError):
            continue
        disease = diseases_by_id.get(did)
        if disease is None:
            continue
        results.append(
            _build_diagnosis_payload_prefetched(diag_id, data, disease, plants_by_id)
        )

    next_page = page + 1 if has_next else None
    previous_page = page - 1 if page > 1 else None
    return {
        "count": total,
        "next": next_page,
        "previous": previous_page,
        "results": results,
    }


def upsert_diseases_for_plant(
    *,
    plant_id: int,
    diseases: list[dict[str, Any]],
    replace: bool = False,
) -> int:
    """Write disease docs for a plant.

    - ``replace=False`` (default): merge-update existing docs; unspecified fields
      in Firestore are preserved (same semantics as ``seed_plant_and_diseases``).
    - ``replace=True``: overwrite each disease document so the new payload is the
      sole source of truth (still ``set()`` so the doc is created if missing).

    Always sets ``plant_id`` and ``updated_at`` on every doc, and invalidates
    the in-process cache afterwards. Returns the number of docs written.
    """
    if not diseases:
        return 0
    client = get_firestore_client()
    batch = client.batch()
    now = datetime.now(timezone.utc)
    for disease in diseases:
        try:
            disease_id = int(disease["id"])
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError(f"Disease entry missing valid integer 'id': {disease!r}") from exc
        dref = client.collection(DISEASES_COLLECTION).document(str(disease_id))
        doc = dict(disease)
        doc.pop("id", None)
        doc["plant_id"] = int(plant_id)
        doc["updated_at"] = now
        batch.set(dref, doc, merge=not replace)
    batch.commit()
    _invalidate_plant(int(plant_id))
    for disease in diseases:
        try:
            _invalidate_disease(int(disease["id"]), int(plant_id))
        except (TypeError, ValueError, KeyError):
            continue
    return len(diseases)


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
    _invalidate_plant(plant_id)
    for disease in diseases:
        try:
            _invalidate_disease(int(disease["id"]), plant_id)
        except (TypeError, ValueError, KeyError):
            continue


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
