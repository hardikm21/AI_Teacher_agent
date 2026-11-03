"""
Lightweight auth for the demo — no external deps.

- Passwords hashed with PBKDF2-SHA256 (stdlib).
- Sessions are opaque random tokens held in-memory, mapped to user_id.
- role gating via `require_role(...)` FastAPI dependency.

Swap the two in-memory dicts for a real DB when persistence matters.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Literal, Optional
from datetime import datetime
import hashlib
import hmac
import secrets
import uuid


Role = Literal["student", "teacher"]


# ── storage (swap for DB) ──────────────────────────────────────────────────

class UserRecord(BaseModel):
    id:         str
    email:      str
    name:       str
    role:       Role
    roll_no:    str = ""
    created_at: datetime


_users_by_email: Dict[str, dict]  = {}   # email -> {record: UserRecord, salt, hash}
_users_by_id:    Dict[str, dict]  = {}   # id    -> same object
_tokens:         Dict[str, str]   = {}   # token -> user_id


# ── hashing ────────────────────────────────────────────────────────────────

def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)


def _make_hash(password: str) -> tuple[bytes, bytes]:
    salt = secrets.token_bytes(16)
    return salt, _hash(password, salt)


def _check_password(password: str, salt: bytes, expected: bytes) -> bool:
    return hmac.compare_digest(_hash(password, salt), expected)


# ── api models ─────────────────────────────────────────────────────────────

class SignupBody(BaseModel):
    email:    str
    password: str = Field(min_length=6)
    name:     str = Field(min_length=1)
    role:     Role = "student"
    roll_no:  str = ""


class LoginBody(BaseModel):
    email:    str
    password: str


class AuthResponse(BaseModel):
    token: str
    user:  UserRecord


# ── operations ─────────────────────────────────────────────────────────────

def signup(body: SignupBody) -> AuthResponse:
    email = body.email.lower().strip()
    if email in _users_by_email:
        raise HTTPException(status_code=409, detail="Email already registered.")

    user_id = str(uuid.uuid4())
    salt, pwd_hash = _make_hash(body.password)

    record = UserRecord(
        id=user_id,
        email=email,
        name=body.name,
        role=body.role,
        roll_no=body.roll_no.strip(),
        created_at=datetime.utcnow(),
    )
    entry = {"record": record, "salt": salt, "hash": pwd_hash}
    _users_by_email[email] = entry
    _users_by_id[user_id]  = entry

    token = _issue_token(user_id)
    from app.persistence import save_store
    save_store()
    return AuthResponse(token=token, user=record)


def login(body: LoginBody) -> AuthResponse:
    email = body.email.lower().strip()
    entry = _users_by_email.get(email)
    if not entry or not _check_password(body.password, entry["salt"], entry["hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = _issue_token(entry["record"].id)
    return AuthResponse(token=token, user=entry["record"])


def _issue_token(user_id: str) -> str:
    tok = secrets.token_urlsafe(32)
    _tokens[tok] = user_id
    return tok


def logout(token: str) -> None:
    _tokens.pop(token, None)


# ── dependencies ───────────────────────────────────────────────────────────

def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def current_user(
    authorization: Optional[str] = Header(default=None),
) -> UserRecord:
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    user_id = _tokens.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    entry = _users_by_id.get(user_id)
    if not entry:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    return entry["record"]


def require_role(*allowed: Role):
    """Usage:  Depends(require_role('teacher'))"""
    def _dep(user: UserRecord = Depends(current_user)) -> UserRecord:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {' | '.join(allowed)}",
            )
        return user
    return _dep
