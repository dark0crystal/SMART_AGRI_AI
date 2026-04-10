"""DRF authentication using Firebase ID tokens (Authorization: Bearer <token>)."""

from __future__ import annotations

from types import SimpleNamespace

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from firebase_admin.exceptions import FirebaseError
from rest_framework import authentication
from rest_framework.exceptions import APIException, AuthenticationFailed


class FirebaseAdminNotConfigured(APIException):
    """Raised when the server has no service account JSON (cannot verify ID tokens)."""

    status_code = 503
    default_code = "firebase_admin_not_configured"
    default_detail = (
        "Firebase Admin is not configured on this server. Set FIREBASE_CREDENTIALS_PATH "
        "(or FIREBASE_CREDENTIALS_JSON / FIREBASE_CREDENTIALS_BASE64) in the environment, "
        "e.g. in backend/.env — see backend/README.md."
    )


class FirebaseAuthentication(authentication.BaseAuthentication):
    """
    Validate `Authorization: Bearer <Firebase ID token>` and attach a lightweight user object.
    Use with `IsAuthenticated` on views that require a signed-in Firebase user.
    """

    www_authenticate_realm = "api"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request)
        if not header:
            return None

        try:
            scheme, _, token = header.decode("utf-8").partition(" ")
        except UnicodeDecodeError as exc:
            raise AuthenticationFailed(_("Invalid authorization header encoding.")) from exc

        if scheme.lower() != "bearer" or not token:
            return None

        try:
            claims = verify_id_token(token.strip())
        except ImproperlyConfigured as exc:
            raise FirebaseAdminNotConfigured() from exc
        except ValueError as exc:
            raise AuthenticationFailed(_("Invalid token.")) from exc
        except FirebaseError as exc:
            raise AuthenticationFailed(_("Invalid or expired Firebase token.")) from exc

        user = SimpleNamespace(
            pk=claims.get("uid"),
            uid=claims.get("uid"),
            email=claims.get("email"),
            firebase_claims=claims,
            is_authenticated=True,
        )
        return (user, None)

    def authenticate_header(self, request):
        return f'Bearer realm="{self.www_authenticate_realm}"'


def verify_id_token(token: str) -> dict:
    """Delegate to shared Firebase client (single app init)."""
    from .firebase_client import verify_id_token as _verify

    return _verify(token)
