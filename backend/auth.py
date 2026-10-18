"""Create-account and log-in endpoints backed by the users table.

Passwords are never stored in plain text. New accounts are hashed as
"pbkdf2_sha256$<iterations>$<salt>$<hex digest>" with a random 16-byte salt
and 600,000 iterations (OWASP's recommendation for PBKDF2-SHA256), so a
leaked database can't be reversed into passwords. The seed users in
campus_customs.db use an older "pbkdf2_sha256$<salt>$<hex digest>" format,
which is still accepted at log-in.

Logged-in shoppers get a signed session token: "<user_id>.<expiry>.<signature>".
"""

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, field_validator

from db import get_db

PBKDF2_ITERATIONS = 600_000
# Iteration count assumed for seed users stored in the older 3-part format.
LEGACY_ITERATIONS = 100_000
MIN_PASSWORD_LENGTH = 8
SESSION_SECONDS = 7 * 24 * 60 * 60
# Set SESSION_SECRET in the environment to keep sessions valid across restarts.
SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

router = APIRouter(prefix="/api")


# ---------- Password hashing ----------

def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = _pbkdf2(password, salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if parts[0] != "pbkdf2_sha256":
        return False
    if len(parts) == 4 and parts[1].isdigit():
        _, iterations, salt, expected = parts
        digest = _pbkdf2(password, salt, int(iterations))
    elif len(parts) == 3:
        _, salt, expected = parts
        digest = _pbkdf2(password, salt, LEGACY_ITERATIONS)
    else:
        return False
    return hmac.compare_digest(digest, expected)


_DUMMY_HASH = hash_password(secrets.token_hex(16))


# ---------- Session tokens ----------

def _sign(payload: str) -> str:
    return hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time()) + SESSION_SECONDS}"
    return f"{payload}.{_sign(payload)}"


def user_id_from_token(token: str) -> int | None:
    try:
        user_id, expiry, signature = token.split(".")
    except ValueError:
        return None
    if not hmac.compare_digest(_sign(f"{user_id}.{expiry}"), signature):
        return None
    if int(expiry) < time.time():
        return None
    return int(user_id)


def current_user_id(authorization: str | None) -> int | None:
    """Return the logged-in user's id from an 'Authorization: Bearer' header, if valid."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return user_id_from_token(authorization.removeprefix("Bearer "))


# ---------- Request / response models ----------

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str

    @field_validator("first_name", "last_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("is required")
        return v

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("must be a valid email address")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut
    # Problem 8: the website lands the shopper on the last product they looked at.
    last_viewed_product_id: str | None = None


def user_out(row: sqlite3.Row) -> UserOut:
    # Older rows may only have the combined "name" column filled in.
    first, _, last = (row["name"] or "").partition(" ")
    return UserOut(
        id=row["id"],
        first_name=row["first_name"] or first,
        last_name=row["last_name"] or last,
        email=row["email"],
    )


# ---------- Endpoints ----------

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest) -> UserOut:
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    if len(body.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
        )

    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE lower(email) = ?", (body.email,)
        ).fetchone()
        if exists:
            raise HTTPException(
                status_code=409, detail="An account with this email already exists."
            )
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                f"{body.first_name} {body.last_name}",
                body.email,
                hash_password(body.password),
                body.first_name,
                body.last_name,
            ),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return user_out(row)


@router.post("/login")
def login(body: LoginRequest) -> LoginResponse:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE lower(email) = ?", (body.email.strip().lower(),)
        ).fetchone()
    # Hash even when the email is unknown so response timing doesn't reveal
    # which emails have accounts.
    stored = row["password_hash"] if row else _DUMMY_HASH
    if not verify_password(body.password, stored) or row is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return LoginResponse(token=create_token(row["id"]), user=user_out(row),
                         last_viewed_product_id=_last_viewed(row["id"]))


def _last_viewed(user_id: int) -> str | None:
    """Most recent product in product_views (see memory.py) for this shopper, if any."""
    try:
        with get_db() as conn:
            r = conn.execute("SELECT product_id FROM product_views WHERE user_id = ? "
                             "ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    except sqlite3.OperationalError:  # table not created yet
        return None
    return r["product_id"] if r else None


@router.get("/me")
def me(authorization: str | None = Header(default=None)) -> UserOut:
    user_id = current_user_id(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not logged in.")
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return user_out(row)
