"""Accounts, password hashing, and login sessions.

Passwords: PBKDF2-HMAC-SHA256 with a random per-user salt.
  - New hashes:   pbkdf2_sha256$<iterations>$<salt>$<hex digest>
  - Seed hashes:  pbkdf2_sha256$<salt>$<hex digest>   (legacy, 120,000 iterations)
  Legacy hashes still verify and are upgraded to the new format on the next login.

Sessions: a random token lives in an HttpOnly cookie; the db stores only its SHA-256.
"""

import hashlib
import hmac
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from db import connect

PBKDF2_ITERATIONS = 600_000  # OWASP 2023+ recommendation for PBKDF2-SHA256
LEGACY_ITERATIONS = 120_000  # what the seed users were hashed with
SESSION_COOKIE = "cc_session"
SESSION_DAYS = 7
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------- password hashing ----------


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) == 4:
        algo, iterations, salt, digest = parts
        iterations = int(iterations)
    elif len(parts) == 3:
        algo, salt, digest = parts
        iterations = LEGACY_ITERATIONS
    else:
        return False
    if algo != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return hmac.compare_digest(candidate, digest)


def needs_rehash(stored: str) -> bool:
    parts = stored.split("$")
    return len(parts) != 4 or int(parts[1]) < PBKDF2_ITERATIONS


# Used when the email doesn't exist, so a failed login takes the same time either way.
_DUMMY_HASH = hash_password(secrets.token_hex(8))


# ---------- sessions ----------


def init_sessions_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def start_session(response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(days=SESSION_DAYS)
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, _token_hash(token), expires.strftime("%Y-%m-%d %H:%M:%S")),
        )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,  # page JavaScript can't read the token
        samesite="lax",  # not sent on cross-site POSTs
        secure=False,  # localhost is plain http; set True when served over https
    )


def current_user(request: Request) -> dict | None:
    """FastAPI dependency: the logged-in user, or None."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.first_name, u.last_name, u.email, u.created_at
            FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > datetime('now')
            """,
            (_token_hash(token),),
        ).fetchone()
    return dict(row) if row else None


def require_user(user: dict | None = Depends(current_user)) -> dict:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in.")
    return user


# ---------- request models ----------


class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("can't be blank")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("enter a valid email address")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


# ---------- routes ----------


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, response: Response) -> dict:
    if body.password != body.confirm_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwords don't match.")
    try:
        with connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO users (name, email, password_hash, first_name, last_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    f"{body.first_name} {body.last_name}",
                    body.email,
                    hash_password(body.password),
                    body.first_name,
                    body.last_name,
                ),
            )
            user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists.")
    start_session(response, user_id)
    return {"id": user_id, "first_name": body.first_name, "last_name": body.last_name, "email": body.email}


@router.post("/login")
def login(body: LoginRequest, response: Response) -> dict:
    email = body.email.strip().lower()
    with connect() as conn:
        row = conn.execute(
            "SELECT id, first_name, last_name, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    if row is None:
        verify_password(body.password, _DUMMY_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    if not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")

    if needs_rehash(row["password_hash"]):
        with connect() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(body.password), row["id"]),
            )
    start_session(response, row["id"])
    return {k: row[k] for k in ("id", "first_name", "last_name", "email")}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(require_user)) -> dict:
    return user
