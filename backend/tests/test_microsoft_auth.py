from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import json

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main as routes
from app import microsoft_auth
from app.auth import create_token, get_current_user, hash_password, require_admin
from app.database import Base
from app.migrations import upgrade_microsoft_identity
from app.models import MicrosoftAuthNonce, MicrosoftIdentity, User
from app.schemas import SignupRequest, UserOut
from app.schemas_auth import MicrosoftTokenRequest

TENANT = "11111111-1111-4111-8111-111111111111"
CLIENT = "22222222-2222-4222-8222-222222222222"
OID = "33333333-3333-4333-8333-333333333333"


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False)
    session = session_local()
    yield session
    session.close()
    engine.dispose()


def add_user(db, role="student", email="student@ssn.edu"):
    user = User(
        name="Test User", email=email, password_hash=hash_password("secret123"),
        role=role, register_number=f"REG-{email}", department="IT", batch="2026",
        cgpa=8.0, arrears=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_nonce(db, nonce):
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)
    db.add(MicrosoftAuthNonce(nonce=nonce, expires_at=expires))
    db.commit()


def test_password_signup_login_and_admin_protection(db):
    student = routes.signup(SignupRequest(
        name="New Student", email="new@ssn.edu", password="secret123",
        register_number="REG-NEW", department="IT", batch="2026", cgpa=8.1, arrears=0,
    ), db)
    assert student.email == "new@ssn.edu"
    assert "password_hash" not in UserOut.model_validate(student).model_dump()
    assert student.password_hash != "secret123"

    student_login = routes.login(OAuth2PasswordRequestForm(username="new@ssn.edu", password="secret123"), db)
    assert student_login["role"] == "student"
    assert student_login["access_token"]

    with pytest.raises(HTTPException) as student_denied:
        require_admin(student)
    assert student_denied.value.status_code == 403

    admin = add_user(db, "admin", "admin@ssn.edu")
    admin.password_hash = hash_password("admin123")
    db.commit()
    admin_login = routes.login(OAuth2PasswordRequestForm(username="admin@ssn.edu", password="admin123"), db)
    assert admin_login["role"] == "admin"
    assert require_admin(admin) is admin


def test_link_requires_existing_student_then_microsoft_login_works(db, monkeypatch):
    student = add_user(db)
    original_password_hash = student.password_hash
    claims = {"tid": TENANT, "oid": OID, "sub": "subject-1", "email": student.email,
              "email_verified": True, "role": "admin", "nonce": "n1"}
    monkeypatch.setattr(routes, "verify_microsoft_id_token", lambda _: claims)
    add_nonce(db, "n1")

    with pytest.raises(HTTPException) as unlinked:
        routes.microsoft_login(MicrosoftTokenRequest(id_token="mocked-valid-signed-token-0001"), db)
    assert unlinked.value.status_code == 409
    assert db.query(User).count() == 1

    password_token = create_token(student)
    authenticated_student = get_current_user(token=password_token, db=db)
    linked = routes.microsoft_link(
        MicrosoftTokenRequest(id_token="mocked-valid-signed-token-0001"), db, authenticated_student
    )
    assert linked["role"] == "student"
    assert linked["access_token"]
    assert password_token
    assert db.query(MicrosoftIdentity).count() == 1
    assert student.password_hash == original_password_hash
    assert (student.name, student.department, student.batch, student.cgpa, student.arrears) == (
        "Test User", "IT", "2026", 8.0, 0,
    )

    claims["nonce"] = "n2"
    add_nonce(db, "n2")
    microsoft_login = routes.microsoft_login(MicrosoftTokenRequest(id_token="mocked-valid-signed-token-0002"), db)
    assert microsoft_login["role"] == "student"
    with pytest.raises(HTTPException) as replayed:
        routes.microsoft_login(MicrosoftTokenRequest(id_token="mocked-valid-signed-token-0002"), db)
    assert replayed.value.status_code == 401


def test_link_rejects_email_mismatch_duplicates_and_admin(db, monkeypatch):
    first = add_user(db)
    second = add_user(db, email="second@ssn.edu")
    admin = add_user(db, "admin", "admin@ssn.edu")
    claims = {"tid": TENANT, "oid": OID, "sub": "subject-1", "email": first.email,
              "email_verified": True, "nonce": "n1"}
    monkeypatch.setattr(routes, "verify_microsoft_id_token", lambda _: claims)

    add_nonce(db, "n1")
    claims["email_verified"] = False
    with pytest.raises(HTTPException) as unverified_email:
        routes.microsoft_link(MicrosoftTokenRequest(id_token="mocked-valid-signed-token-0001"), db, first)
    assert unverified_email.value.status_code == 400
    claims["email_verified"] = True
    with pytest.raises(HTTPException) as wrong_email:
        routes.microsoft_link(MicrosoftTokenRequest(id_token="mocked-valid-signed-token-0001"), db, second)
    assert wrong_email.value.status_code == 400
    linked = routes.microsoft_link(MicrosoftTokenRequest(id_token="mocked-valid-signed-token-0001"), db, first)
    assert linked["role"] == "student"

    claims.update(oid="55555555-5555-4555-8555-555555555555", nonce="n-link-again")
    add_nonce(db, "n-link-again")
    with pytest.raises(HTTPException) as second_identity:
        routes.microsoft_link(MicrosoftTokenRequest(id_token="mocked-valid-signed-token-0002"), db, first)
    assert second_identity.value.status_code == 409

    claims.update(oid=OID, email=second.email, nonce="n2")
    add_nonce(db, "n2")
    with pytest.raises(HTTPException) as duplicate_identity:
        routes.microsoft_link(MicrosoftTokenRequest(id_token="mocked-valid-signed-token-0002"), db, second)
    assert duplicate_identity.value.status_code == 409

    claims.update(email=admin.email, nonce="n3")
    add_nonce(db, "n3")
    with pytest.raises(HTTPException) as admin_link:
        routes.microsoft_link(MicrosoftTokenRequest(id_token="mocked-valid-signed-token-0003"), db, admin)
    assert admin_link.value.status_code == 403

    db.add(MicrosoftIdentity(
        tenant_id=TENANT, object_id="44444444-4444-4444-8444-444444444444", user_id=admin.id,
    ))
    db.commit()
    claims.update(oid="44444444-4444-4444-8444-444444444444")
    with pytest.raises(HTTPException) as admin_login:
        routes.microsoft_login(MicrosoftTokenRequest(id_token="mocked-valid-signed-token-0003"), db)
    assert admin_login.value.status_code == 403


@pytest.fixture
def rsa_tokens(monkeypatch):
    monkeypatch.setenv("ENTRA_CLIENT_ID", CLIENT)
    monkeypatch.setenv("ENTRA_TENANT_ID", TENANT)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    class FakeJwkClient:
        def __init__(self, _url):
            pass

        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=public_key)

    monkeypatch.setattr(microsoft_auth, "PyJWKClient", FakeJwkClient)
    monkeypatch.setattr(microsoft_auth, "get_openid_metadata", lambda tenant: {
        "issuer": f"https://login.microsoftonline.com/{tenant}/v2.0",
        "jwks_uri": f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
    })

    def make(**changes):
        now = datetime.now(timezone.utc)
        claims = {
            "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0",
            "aud": CLIENT, "tid": TENANT, "oid": OID, "sub": "subject-1",
            "iat": now, "nbf": now - timedelta(seconds=2), "exp": now + timedelta(minutes=5),
            "nonce": "nonce-valid",
        }
        claims.update(changes)
        return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test"})

    return make, other_key


def test_verified_token_rejects_bad_signature_audience_expiry_tenant_and_claims(rsa_tokens):
    make, other_key = rsa_tokens
    assert microsoft_auth.verify_microsoft_id_token(make())["oid"] == OID

    wrong_signature = jwt.encode(
        {"iss": f"https://login.microsoftonline.com/{TENANT}/v2.0", "aud": CLIENT,
         "tid": TENANT, "oid": OID, "sub": "s", "iat": datetime.now(timezone.utc),
         "nbf": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
         "nonce": "nonce-valid"},
        other_key, algorithm="RS256", headers={"kid": "test"},
    )
    for token in (
        wrong_signature,
        make(aud="wrong-audience"),
        make(iss="https://login.microsoftonline.com/common/v2.0"),
        make(exp=datetime.now(timezone.utc) - timedelta(minutes=1)),
        make(tid="99999999-9999-4999-8999-999999999999"),
        make(oid=None),
        make(oid="not-a-guid"),
        make(sub=None),
        make(tid=42),
        make(nonce=None),
    ):
        with pytest.raises(HTTPException):
            microsoft_auth.verify_microsoft_id_token(token)


def test_missing_or_malformed_configuration_fails_safely(monkeypatch):
    monkeypatch.delenv("ENTRA_CLIENT_ID", raising=False)
    monkeypatch.delenv("ENTRA_TENANT_ID", raising=False)
    with pytest.raises(HTTPException) as missing:
        microsoft_auth.microsoft_settings()
    assert missing.value.status_code == 503
    assert "ENTRA_CLIENT_ID" in missing.value.detail
    assert "ENTRA_TENANT_ID" in missing.value.detail

    monkeypatch.setenv("ENTRA_CLIENT_ID", "not-a-guid")
    monkeypatch.setenv("ENTRA_TENANT_ID", TENANT)
    with pytest.raises(HTTPException) as malformed:
        microsoft_auth.microsoft_settings()
    assert malformed.value.status_code == 503


def test_backend_environment_loads_from_its_env_file_without_overriding_process_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(f"ENTRA_CLIENT_ID={CLIENT}\nENTRA_TENANT_ID={TENANT}\n")
    monkeypatch.setattr(microsoft_auth, "BACKEND_ENV_FILE", env_file)
    monkeypatch.delenv("ENTRA_CLIENT_ID", raising=False)
    monkeypatch.delenv("ENTRA_TENANT_ID", raising=False)

    microsoft_auth.load_backend_environment()
    assert microsoft_auth.microsoft_settings() == (CLIENT, TENANT)

    monkeypatch.setenv("ENTRA_CLIENT_ID", "44444444-4444-4444-8444-444444444444")
    microsoft_auth.load_backend_environment()
    assert microsoft_auth.microsoft_settings()[0] == "44444444-4444-4444-8444-444444444444"


def test_openid_metadata_accepts_only_configured_microsoft_issuer_and_keys(monkeypatch):
    class MetadataResponse:
        def __init__(self, content):
            self.content = content

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return self.content

    metadata = {
        "issuer": f"https://login.microsoftonline.com/{TENANT}/v2.0",
        "jwks_uri": f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys",
    }
    monkeypatch.setattr(microsoft_auth.urllib.request, "urlopen", lambda *_args, **_kwargs: MetadataResponse(
        json.dumps(metadata).encode()
    ))
    microsoft_auth.get_openid_metadata.cache_clear()
    assert microsoft_auth.get_openid_metadata(TENANT) == metadata
    microsoft_auth.get_openid_metadata.cache_clear()

    metadata["jwks_uri"] = "https://attacker.example/keys"
    with pytest.raises(HTTPException) as untrusted:
        microsoft_auth.get_openid_metadata(TENANT)
    assert untrusted.value.status_code == 503
    microsoft_auth.get_openid_metadata.cache_clear()


def test_schema_upgrade_preserves_existing_data_and_verifies_backup(tmp_path):
    path = tmp_path / "existing.db"
    import sqlite3

    with sqlite3.connect(path) as database:
        database.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, password_hash TEXT, role TEXT,
                register_number TEXT, department TEXT, batch TEXT, cgpa FLOAT, arrears INTEGER);
            CREATE TABLE drives (id INTEGER PRIMARY KEY, company TEXT);
            CREATE TABLE applications (id INTEGER PRIMARY KEY, student_id INTEGER, drive_id INTEGER);
            INSERT INTO users VALUES (1, 'Student', 'student@ssn.edu', 'hash', 'student', 'R1', 'IT', '2026', 8, 0);
            INSERT INTO users VALUES (2, 'Admin', 'admin@ssn.edu', 'hash2', 'admin', 'R2', 'IT', '2026', 0, 0);
            INSERT INTO drives VALUES (1, 'Company');
            INSERT INTO applications VALUES (1, 1, 1);
        """)

    backup = upgrade_microsoft_identity(str(path))
    assert backup and Path(backup).exists()
    with sqlite3.connect(path) as database:
        assert database.execute("select count(*) from users").fetchone()[0] == 2
        assert database.execute("select count(*) from drives").fetchone()[0] == 1
        assert database.execute("select count(*) from applications").fetchone()[0] == 1
        assert database.execute("select count(*) from microsoft_identities").fetchone()[0] == 0
        assert database.execute("select count(*) from microsoft_auth_nonces").fetchone()[0] == 0
    with sqlite3.connect(backup) as database:
        assert database.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert database.execute("select count(*) from users").fetchone()[0] == 2
