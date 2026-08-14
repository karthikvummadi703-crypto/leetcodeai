"""
Firebase token verification and FastAPI authentication dependencies.
"""

from __future__ import annotations

from typing import Any

import firebase_admin
from fastapi import Request
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.config import get_settings
from app.core import AuthenticationError, get_logger
from app.schemas import UserProfile

log = get_logger("auth")

_firebase_app: firebase_admin.App | None = None


def _init_firebase() -> None:
    """
    Lazily initialise the Firebase Admin SDK using env-var credentials.
    Safe to call multiple times — only the first call has an effect.
    """
    global _firebase_app
    if _firebase_app is not None:
        return

    settings = get_settings()

    if not settings.firebase_project_id:
        log.warning("Firebase credentials not configured — auth will reject all tokens")
        return

    # Build a credential dict from individual env vars so we never need
    # a service-account JSON file on disk.
    cred_dict: dict[str, Any] = {
        "type": "service_account",
        "project_id": settings.firebase_project_id,
        "client_email": settings.firebase_client_email,
        "private_key": settings.firebase_private_key.replace("\\n", "\n"),
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    try:
        cred = credentials.Certificate(cred_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        log.info(
            "Firebase Admin SDK initialised for project {pid}", pid=settings.firebase_project_id
        )
    except Exception as exc:  # noqa: BLE001 - init failure is non-fatal (app still runs unauthenticated)
        log.error("Failed to initialise Firebase Admin SDK: {exc}", exc=exc)


def get_firebase_app() -> firebase_admin.App | None:
    """
    Return the initialised Firebase Admin app, or None if Firebase is
    not configured (or initialisation failed).
    """
    _init_firebase()
    return _firebase_app


def verify_token(id_token: str) -> dict[str, Any]:
    """
    Verify a Firebase ID token and return the decoded claims dict.

    Raises:
        AuthenticationError on any verification failure.
    """
    _init_firebase()

    if _firebase_app is None:
        raise AuthenticationError("Firebase is not configured on the server.")

    try:
        decoded = firebase_auth.verify_id_token(id_token, app=_firebase_app)
        return decoded
    except firebase_auth.ExpiredIdTokenError:
        raise AuthenticationError("Token has expired. Please sign in again.") from None
    except firebase_auth.RevokedIdTokenError:
        raise AuthenticationError("Token has been revoked.") from None
    except firebase_auth.InvalidIdTokenError:
        raise AuthenticationError("Invalid authentication token.") from None
    except Exception as exc:
        log.error("Token verification failed: {exc}", exc=exc)
        raise AuthenticationError("Authentication failed.") from exc


def _extract_bearer_token(request: Request) -> str:
    """Pull the Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing or malformed Authorization header.")
    return auth_header[7:]


async def get_current_user(request: Request) -> UserProfile:
    """
    FastAPI dependency — extracts and verifies the Firebase ID token
    from the request and returns a UserProfile.
    """
    token = _extract_bearer_token(request)
    claims = verify_token(token)

    return UserProfile(
        uid=claims.get("uid", claims.get("user_id", "")),
        email=claims.get("email"),
        display_name=claims.get("name"),
        photo_url=claims.get("picture"),
    )
