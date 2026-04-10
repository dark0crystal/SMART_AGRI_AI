"""
Firebase Admin SDK: Auth token verification, Firestore, Cloud Storage, Realtime Database.

Initialize with FIREBASE_CREDENTIALS_PATH (JSON file) or FIREBASE_CREDENTIALS_JSON.
Optional: FIREBASE_STORAGE_BUCKET, FIREBASE_DATABASE_URL (Realtime DB), FIREBASE_PROJECT_ID.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

import firebase_admin
from firebase_admin import credentials


def _resolve_credentials_path(path: str) -> str:
    """Allow FIREBASE_CREDENTIALS_PATH relative to Django BASE_DIR (not shell cwd)."""
    p = Path(path)
    if p.is_absolute():
        return str(p)
    base_dir = getattr(settings, "BASE_DIR", None)
    if base_dir is not None:
        return str(Path(base_dir) / path)
    return str(p.resolve())


def _firebase_credentials() -> credentials.Base:
    path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None)
    raw_json = getattr(settings, "FIREBASE_CREDENTIALS_JSON", None)
    b64_json = getattr(settings, "FIREBASE_CREDENTIALS_BASE64", None)

    if path:
        return credentials.Certificate(_resolve_credentials_path(path))

    if raw_json:
        return credentials.Certificate(json.loads(raw_json))

    if b64_json:
        import base64

        decoded = base64.b64decode(b64_json).decode("utf-8")
        return credentials.Certificate(json.loads(decoded))

    raise ImproperlyConfigured(
        "Firebase is not configured: set FIREBASE_CREDENTIALS_PATH, "
        "FIREBASE_CREDENTIALS_JSON, or FIREBASE_CREDENTIALS_BASE64 in the environment "
        "(see Django settings)."
    )


def _firebase_app_options() -> dict[str, Any]:
    options: dict[str, Any] = {}
    project_id = getattr(settings, "FIREBASE_PROJECT_ID", None)
    storage_bucket = getattr(settings, "FIREBASE_STORAGE_BUCKET", None)
    database_url = getattr(settings, "FIREBASE_DATABASE_URL", None)

    if project_id:
        options["projectId"] = project_id
    if storage_bucket:
        options["storageBucket"] = storage_bucket
    if database_url:
        options["databaseURL"] = database_url

    return options


def get_firebase_app() -> firebase_admin.App:
    """Return the default Firebase app, initializing it on first use."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        cred = _firebase_credentials()
        options = _firebase_app_options()
        return firebase_admin.initialize_app(cred, options or None)


def verify_id_token(id_token: str, check_revoked: bool = False) -> dict[str, Any]:
    """
    Verify a Firebase ID token from the client (Authorization: Bearer ...).
    Returns decoded claims (includes 'uid', 'email', etc.).
    """
    from firebase_admin import auth

    get_firebase_app()
    return auth.verify_id_token(id_token, check_revoked=check_revoked)


def get_firestore_client():
    """Firestore client for server-side reads/writes."""
    from firebase_admin import firestore

    get_firebase_app()
    return firestore.client()


def get_storage_bucket(name: str | None = None):
    """
    Default Cloud Storage bucket for this project (or pass an explicit bucket name).
    """
    from firebase_admin import storage

    get_firebase_app()
    if name:
        return storage.bucket(name)
    return storage.bucket()


def get_rtdb_reference(path: str = "/"):
    """
    Realtime Database root or child reference.
    Requires FIREBASE_DATABASE_URL in settings / Firebase app options.
    """
    from firebase_admin import db

    get_firebase_app()
    if not getattr(settings, "FIREBASE_DATABASE_URL", None):
        raise ImproperlyConfigured(
            "Firebase Realtime Database requires FIREBASE_DATABASE_URL "
            "(e.g. https://<project>.firebaseio.com)."
        )
    return db.reference(path)
