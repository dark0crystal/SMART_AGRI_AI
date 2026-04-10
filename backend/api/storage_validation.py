"""Validate Firebase Storage (or allowlisted) HTTPS image URLs before persisting."""

from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings


def is_allowed_storage_image_url(url: str) -> bool:
    """
    Accept only https URLs that match optional allowlist / Firebase bucket rules.
    If no rules are configured, accept any https URL (local dev only).
    """
    parsed = urlparse(url.strip())
    if parsed.scheme != "https":
        return False

    prefixes = getattr(settings, "ALLOWED_STORAGE_IMAGE_URL_PREFIXES", None) or ""
    parts = [p.strip() for p in prefixes.split(",") if p.strip()]
    if parts:
        return any(url.startswith(p) for p in parts)

    bucket = getattr(settings, "FIREBASE_STORAGE_BUCKET", None) or ""
    if bucket:
        # Typical download URLs include the bucket id in the path.
        return (
            f"/v0/b/{bucket}/" in url
            or f"/b/{bucket}/" in url
            or bucket in url
        )

    # Dev fallback: any https (tighten in production by setting bucket or prefixes).
    return True
