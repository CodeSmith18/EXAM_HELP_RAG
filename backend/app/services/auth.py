from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Optional

from fastapi import Header, HTTPException, status

from app import database
from app.config import get_settings
from app.models import AuthLoginRequest, AuthRegisterRequest, AuthResponse, UserOut


PASSWORD_ITERATIONS = 210_000
TOKEN_ALGORITHM = "HS256"


def b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str, salt: Optional[str] = None) -> str:
    password_salt = salt or secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        password_salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${password_salt}${b64url_encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, raw_iterations, salt, expected_digest = stored_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False

    iterations = int(raw_iterations)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return secrets.compare_digest(b64url_encode(digest), expected_digest)


def sign_token(payload: dict[str, Any]) -> str:
    settings = get_settings()
    header = {"alg": TOKEN_ALGORITHM, "typ": "JWT"}
    encoded_header = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(settings.auth_secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{b64url_encode(signature)}"


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
        signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
        expected_signature = hmac.new(settings.auth_secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not secrets.compare_digest(b64url_encode(expected_signature), encoded_signature):
            raise ValueError("Invalid token signature.")
        payload = json.loads(b64url_decode(encoded_payload))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token has expired.")
    return payload


def create_access_token(user: dict[str, Any]) -> str:
    settings = get_settings()
    now = int(time.time())
    return sign_token(
        {
            "sub": user["id"],
            "email": user["email"],
            "iat": now,
            "exp": now + settings.access_token_minutes * 60,
        }
    )


def auth_response(user: dict[str, Any]) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user), user=UserOut(**user))


def register_user(request: AuthRegisterRequest) -> AuthResponse:
    email = normalize_email(request.email)
    if database.get_user_by_email(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account already exists for this email.")
    user = database.create_user(
        email=email,
        password_hash=hash_password(request.password),
        full_name=request.full_name.strip() if request.full_name else None,
    )
    return auth_response(user)


def login_user(request: AuthLoginRequest) -> AuthResponse:
    user = database.get_user_by_email(normalize_email(request.email))
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    return auth_response(user)


def get_current_user(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> UserOut:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    user = database.get_user(str(payload.get("sub", "")))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account was not found.")
    return UserOut(**user)
