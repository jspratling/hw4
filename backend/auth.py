"""Create-account, log-in and password-reset endpoints backed by the users table.

Passwords are never stored in plain text. Every account (the seeded users and
new sign-ups) uses the same settings: PBKDF2-HMAC-SHA256, 120,000 iterations,
a random salt, stored as "pbkdf2_sha256$<salt>$<hex digest>". Log-in reads the
salt from the stored string, re-hashes what the shopper typed with that salt
and compares the two with a constant-time compare.

After 3 failed log-ins for the same email the shopper is prompted to change
their password and a reset link is sent to the email on file (see mailer.py).

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

import mailer
from db import get_db

# Same settings as the seeded users in campus_customs.db (from the assignment).
PBKDF2_ITERATIONS = 120_000
MAX_FAILED_LOGINS = 3
RESET_LINK_MINUTES = 30
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
    salt = secrets.token_hex(8)
    digest = _pbkdf2(password, salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if parts[0] != "pbkdf2_sha256":
        return False
    if len(parts) == 3:  # the standard format: pbkdf2_sha256$salt$hash
        _, salt, expected = parts
        digest = _pbkdf2(password, salt, PBKDF2_ITERATIONS)
    elif len(parts) == 4 and parts[1].isdigit():
        # Two test accounts were made by an earlier version that stored the iteration
        # count. They still log in, and are re-saved in the standard format (see login).
        _, iterations, salt, expected = parts
        digest = _pbkdf2(password, salt, int(iterations))
    else:
        return False
    return hmac.compare_digest(digest, expected)


def needs_rehash(stored: str) -> bool:
    return len(stored.split("$")) != 3


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
    email = body.email.strip().lower()
    with get_db() as conn:
        init_auth_tables(conn)
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
    # Hash even when the email is unknown so response timing doesn't reveal
    # which emails have accounts.
    stored = row["password_hash"] if row else _DUMMY_HASH
    if not verify_password(body.password, stored) or row is None:
        if _record_failure(email):
            # Third miss: prompt a password change and email a reset link. The message is
            # the same whether or not the email has an account, so it can't be used to
            # find out who shops here.
            if row is not None:
                _send_reset_link(row)
            raise HTTPException(
                status_code=401,
                detail=("That's 3 incorrect tries. For your security, please change your "
                        "password. If an account uses this email, we've sent a password "
                        "reset link to the email address on file."),
                headers={"X-Password-Reset": "prompt"},
            )
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    with get_db() as conn:
        conn.execute("DELETE FROM login_failures WHERE email = ?", (email,))
        if needs_rehash(stored):
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                         (hash_password(body.password), row["id"]))
    return LoginResponse(token=create_token(row["id"]), user=user_out(row),
                         last_viewed_product_id=_last_viewed(row["id"]))


# ---------- Failed log-ins and password reset ----------

def init_auth_tables(conn: sqlite3.Connection) -> None:
    """Tables for failed log-in counts and reset links. Neither one stores a password."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS login_failures (
            email TEXT PRIMARY KEY,
            count INTEGER NOT NULL,
            last_failed_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            token_hash TEXT NOT NULL UNIQUE,
            expires_at INTEGER NOT NULL,
            used_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""")


def _record_failure(email: str) -> bool:
    """Count a failed log-in. Returns True on the 3rd miss (and starts the count again)."""
    with get_db() as conn:
        init_auth_tables(conn)
        conn.execute(
            "INSERT INTO login_failures (email, count) VALUES (?, 1) "
            "ON CONFLICT(email) DO UPDATE SET count = count + 1, last_failed_at = datetime('now')",
            (email,))
        count = conn.execute("SELECT count FROM login_failures WHERE email = ?", (email,)).fetchone()[0]
        if count >= MAX_FAILED_LOGINS:
            conn.execute("DELETE FROM login_failures WHERE email = ?", (email,))
            return True
    return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _send_reset_link(row: sqlite3.Row) -> None:
    """Make a one-time link that works for 30 minutes and email it to the address on file.

    Only a hash of the link's token is saved, so a leaked database can't be used to
    reset anyone's password.
    """
    token = secrets.token_urlsafe(32)
    with get_db() as conn:
        init_auth_tables(conn)
        conn.execute("INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
                     (row["id"], _token_hash(token), int(time.time()) + RESET_LINK_MINUTES * 60))
    mailer.send_password_reset(row["email"], user_out(row).first_name, token, RESET_LINK_MINUTES)


class ResetRequest(BaseModel):
    email: str


class ResetConfirm(BaseModel):
    token: str
    password: str
    confirm_password: str


@router.post("/password-reset/request")
def request_password_reset(body: ResetRequest) -> dict:
    """'Forgot password?' on the log-in page. Same answer whether or not the email has an account."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?",
                           (body.email.strip().lower(),)).fetchone()
    if row is not None:
        _send_reset_link(row)
    return {"message": "If an account uses this email, we've sent a password reset link to it."}


@router.post("/password-reset/confirm")
def confirm_password_reset(body: ResetConfirm) -> dict:
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    if len(body.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400,
                            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    with get_db() as conn:
        init_auth_tables(conn)
        reset = conn.execute(
            "SELECT * FROM password_resets WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?",
            (_token_hash(body.token), int(time.time()))).fetchone()
        if reset is None:
            raise HTTPException(status_code=400,
                                detail="This reset link is invalid or has expired. Please ask for a new one.")
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                     (hash_password(body.password), reset["user_id"]))
        # Use up this link and any other open links for the same account.
        conn.execute("UPDATE password_resets SET used_at = datetime('now') "
                     "WHERE user_id = ? AND used_at IS NULL", (reset["user_id"],))
        email = conn.execute("SELECT email FROM users WHERE id = ?", (reset["user_id"],)).fetchone()[0]
        conn.execute("DELETE FROM login_failures WHERE email = ?", (email.lower(),))
    return {"message": "Your password has been changed. You can log in now."}


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
