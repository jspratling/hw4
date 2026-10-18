"""Problem 4: create account, log in, show-password rules and password reset.

Run with:  cd backend  then  .venv\\Scripts\\python.exe -m pytest tests/test_auth.py -v
Uses a temporary copy of campus_customs.db and a temporary email outbox, so real
accounts never change and no email is really sent.
"""

import email
import hashlib
from email import policy
import re
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import auth  # noqa: E402
import db  # noqa: E402
import mailer  # noqa: E402
import main  # noqa: E402
import memory  # noqa: E402

# Made-up test account (not a real person).
EMAIL = "pat.tester@example.edu"
PASSWORD = "elm-city-2026"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    path = tmp_path / "campus_customs.db"
    shutil.copy(db.DB_PATH, path)
    for module in (db, memory, main):
        monkeypatch.setattr(module, "DB_PATH", path)
    monkeypatch.setattr(mailer, "OUTBOX_DIR", tmp_path / "outbox")
    for var in ("SMTP_HOST", "SITE_URL"):
        monkeypatch.delenv(var, raising=False)
    memory.init_memory_tables()
    client = TestClient(main.app)
    r = client.post("/api/register", json={"first_name": "Pat", "last_name": "Tester", "email": EMAIL,
                                           "password": PASSWORD, "confirm_password": PASSWORD})
    assert r.status_code == 201
    return client, path, tmp_path / "outbox"


def read_email(file):
    msg = email.message_from_bytes(file.read_bytes(), policy=policy.default)
    return f"To: {msg['To']}\n" + msg.get_content()


def stored_hash(path, email=EMAIL):
    with sqlite3.connect(path) as conn:
        return conn.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()[0]


def login(client, password, email=EMAIL):
    return client.post("/api/login", json={"email": email, "password": password})


def test_new_accounts_use_the_assignment_hash_settings(env):
    _, path, _ = env
    prefix, salt, digest = stored_hash(path).split("$")
    assert prefix == "pbkdf2_sha256"
    assert digest == hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), salt.encode(), 120_000).hex()
    assert PASSWORD not in stored_hash(path)


def test_seeded_style_hash_logs_in(env):
    """A user stored like the seed data (pbkdf2_sha256$salt$hash, 120,000 iterations) can log in."""
    client, path, _ = env
    salt = "seedsalt0001"
    digest = hashlib.pbkdf2_hmac("sha256", b"seeded-pass-1", salt.encode(), 120_000).hex()
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE email = ?",
                     (f"pbkdf2_sha256${salt}${digest}", EMAIL))
    assert login(client, "seeded-pass-1").status_code == 200
    assert login(client, "wrong-pass-1").status_code == 401


def test_old_four_part_hash_still_works_and_is_upgraded(env):
    client, path, _ = env
    salt = "oldsalt"
    digest = hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), salt.encode(), 600_000).hex()
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE email = ?",
                     (f"pbkdf2_sha256$600000${salt}${digest}", EMAIL))
    assert login(client, PASSWORD).status_code == 200
    assert len(stored_hash(path).split("$")) == 3
    assert login(client, PASSWORD).status_code == 200


def test_login_response_never_contains_the_password_or_hash(env):
    client, path, _ = env
    text = login(client, PASSWORD).text
    assert PASSWORD not in text
    assert stored_hash(path) not in text


def test_three_failed_logins_prompt_a_change_and_email_a_reset_link(env):
    client, path, outbox = env
    for _ in range(2):
        r = login(client, "nope-nope-1")
        assert r.status_code == 401 and "X-Password-Reset" not in r.headers
    assert not outbox.exists()
    r = login(client, "nope-nope-1")
    assert r.status_code == 401
    assert r.headers["X-Password-Reset"] == "prompt"
    assert "change your password" in r.json()["detail"]
    emails = list(outbox.glob("*.eml"))
    assert len(emails) == 1
    body = read_email(emails[0])
    assert f"To: {EMAIL}" in body
    assert PASSWORD not in body and "nope-nope-1" not in body
    token = re.search(r"/reset-password\?token=(\S+)", body).group(1)
    # Only a hash of the token is stored.
    with sqlite3.connect(path) as conn:
        saved = [r[0] for r in conn.execute("SELECT token_hash FROM password_resets")]
    assert token not in saved and hashlib.sha256(token.encode()).hexdigest() in saved


def test_unknown_email_gets_the_same_prompt_but_no_email(env):
    client, _, outbox = env
    for _ in range(3):
        r = login(client, "whatever-1", email="nobody@example.edu")
    assert r.headers["X-Password-Reset"] == "prompt"
    assert not list(outbox.glob("*.eml")) if outbox.exists() else True


def test_successful_login_resets_the_count(env):
    client, _, outbox = env
    login(client, "nope-nope-1")
    login(client, "nope-nope-1")
    assert login(client, PASSWORD).status_code == 200
    r = login(client, "nope-nope-1")
    assert "X-Password-Reset" not in r.headers
    assert not outbox.exists()


def reset_token(client, outbox):
    client.post("/api/password-reset/request", json={"email": EMAIL})
    body = read_email(sorted(outbox.glob("*.eml"))[-1])
    return re.search(r"/reset-password\?token=(\S+)", body).group(1)


def test_reset_link_changes_the_password_once(env):
    client, _, outbox = env
    token = reset_token(client, outbox)
    new = "new-bulldog-77"
    r = client.post("/api/password-reset/confirm",
                    json={"token": token, "password": new, "confirm_password": new})
    assert r.status_code == 200
    assert login(client, PASSWORD).status_code == 401
    assert login(client, new).status_code == 200
    again = client.post("/api/password-reset/confirm",
                        json={"token": token, "password": "another-pass-9", "confirm_password": "another-pass-9"})
    assert again.status_code == 400


def test_reset_rejects_bad_tokens_and_mismatched_passwords(env):
    client, _, outbox = env
    token = reset_token(client, outbox)
    bad = client.post("/api/password-reset/confirm",
                      json={"token": "made-up", "password": "abcdefgh1", "confirm_password": "abcdefgh1"})
    assert bad.status_code == 400
    mismatch = client.post("/api/password-reset/confirm",
                           json={"token": token, "password": "abcdefgh1", "confirm_password": "abcdefgh2"})
    assert mismatch.status_code == 400 and "match" in mismatch.json()["detail"]


def test_expired_reset_link_is_refused(env):
    client, path, outbox = env
    token = reset_token(client, outbox)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE password_resets SET expires_at = 0")
    r = client.post("/api/password-reset/confirm",
                    json={"token": token, "password": "abcdefgh1", "confirm_password": "abcdefgh1"})
    assert r.status_code == 400


def test_forgot_password_answer_is_the_same_for_unknown_emails(env):
    client, _, _ = env
    a = client.post("/api/password-reset/request", json={"email": EMAIL}).json()
    b = client.post("/api/password-reset/request", json={"email": "nobody@example.edu"}).json()
    assert a == b


def test_password_fields_hide_text_show_toggle_and_never_prefill():
    src = BACKEND.parent / "frontend" / "src"
    field = (src / "components" / "PasswordInput.tsx").read_text()
    assert "type={visible ? 'text' : 'password'}" in field
    assert "Show password" in field and 'autoComplete="off"' in field
    for page in ("LoginPage.tsx", "RegisterPage.tsx", "ResetPasswordPage.tsx"):
        text = (src / "pages" / page).read_text()
        assert "<PasswordInput" in text
        assert 'type="password"' not in text  # every password box uses the eye toggle
    login_page = (src / "pages" / "LoginPage.tsx").read_text()
    assert "useState('')" in login_page and "setPassword('')" in login_page
