"""Microsoft Entra ID token validation and account linking."""

import json
import os
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from uuid import UUID
from urllib.parse import urlparse

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError, PyJWTError
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .models import MicrosoftAuthNonce

BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def load_backend_environment() -> None:
    load_dotenv(dotenv_path=BACKEND_ENV_FILE, override=False)


load_backend_environment()


def microsoft_settings() -> tuple[str, str]:
    client_id = os.getenv("ENTRA_CLIENT_ID")
    tenant_id = os.getenv("ENTRA_TENANT_ID")
    missing = []
    if not client_id:
        missing.append("ENTRA_CLIENT_ID")
    if not tenant_id:
        missing.append("ENTRA_TENANT_ID")
    if missing:
        raise HTTPException(
            status_code=503,
            detail="Microsoft sign-in is not configured. Set " + " and ".join(missing) + ".",
        )
    try:
        client_id = str(UUID(client_id))
        tenant_id = str(UUID(tenant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail="Microsoft sign-in configuration is invalid. ENTRA_CLIENT_ID and ENTRA_TENANT_ID must be GUIDs.",
        ) from exc
    return client_id, tenant_id


@lru_cache(maxsize=4)
def get_openid_metadata(tenant_id: str) -> dict:
    url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            metadata = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Microsoft sign-in metadata is unavailable.") from exc
    expected_issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=503, detail="Microsoft returned invalid sign-in metadata.")
    parsed_jwks = urlparse(metadata.get("jwks_uri", ""))
    if metadata.get("issuer") != expected_issuer or (
        parsed_jwks.scheme != "https"
        or parsed_jwks.netloc != "login.microsoftonline.com"
        or parsed_jwks.path != f"/{tenant_id}/discovery/v2.0/keys"
    ):
        raise HTTPException(status_code=503, detail="Microsoft returned untrusted sign-in metadata.")
    return metadata


def verify_microsoft_id_token(id_token: str) -> dict:
    """Verify a v2 ID token against the configured tenant's Microsoft keys."""
    client_id, tenant_id = microsoft_settings()
    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    try:
        metadata = get_openid_metadata(tenant_id)
        signing_key = PyJWKClient(metadata["jwks_uri"]).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=issuer,
            options={"require": ["exp", "iat", "nbf", "tid", "oid", "sub", "nonce"]},
        )
    except PyJWKClientError as exc:
        raise HTTPException(status_code=503, detail="Microsoft signing keys could not be reached.") from exc
    except PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Microsoft sign-in token is invalid or expired.") from exc

    token_tenant = claims.get("tid")
    object_id = claims.get("oid")
    subject = claims.get("sub")
    if not isinstance(token_tenant, str) or not isinstance(object_id, str) or not isinstance(subject, str):
        raise HTTPException(status_code=401, detail="Microsoft token is missing required identity claims.")
    try:
        token_tenant = str(UUID(token_tenant))
        object_id = str(UUID(object_id))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Microsoft token contains malformed identity claims.") from exc
    if token_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Only SSN college Microsoft accounts can sign in.")
    if not object_id or not subject:
        raise HTTPException(status_code=401, detail="Microsoft token is missing required identity claims.")
    claims["tid"] = token_tenant
    claims["oid"] = object_id
    return claims


def issue_microsoft_nonce(db: Session) -> str:
    now = datetime.now(timezone.utc)
    db.query(MicrosoftAuthNonce).filter(MicrosoftAuthNonce.expires_at < now.replace(tzinfo=None)).delete()
    nonce = secrets.token_urlsafe(32)
    db.add(MicrosoftAuthNonce(nonce=nonce, expires_at=(now + timedelta(minutes=5)).replace(tzinfo=None)))
    db.commit()
    return nonce


def check_microsoft_nonce(claims: dict, db: Session, *, consume: bool) -> None:
    nonce = claims.get("nonce")
    if consume:
        result = db.execute(delete(MicrosoftAuthNonce).where(
            MicrosoftAuthNonce.nonce == nonce,
            MicrosoftAuthNonce.expires_at >= datetime.now(timezone.utc).replace(tzinfo=None),
        ))
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=401, detail="Microsoft sign-in request expired. Please try again.")
        db.commit()
    else:
        stored = db.query(MicrosoftAuthNonce).filter(
            MicrosoftAuthNonce.nonce == nonce,
            MicrosoftAuthNonce.expires_at >= datetime.now(timezone.utc).replace(tzinfo=None),
        ).first()
        if stored is None:
            raise HTTPException(status_code=401, detail="Microsoft sign-in request expired. Please try again.")
