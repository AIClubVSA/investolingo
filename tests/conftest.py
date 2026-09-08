"""Integration fixtures. Test dependencies: pytest, httpx, backend requirements."""

import importlib
import smtplib
import socket
import sqlite3
import sys
from contextlib import ExitStack
from itertools import count

import pytest
from fastapi.testclient import TestClient


PASSWORD = "Integration-password-42!"


def ok(response):
    assert 200 <= response.status_code < 300, response.text
    return response.json()


def denied(response, statuses=(400, 401, 403, 404, 409, 422)):
    assert response.status_code in statuses, response.text
    assert "detail" in response.json(), response.text


def post(client, path, payload=None):
    csrf = ok(client.get("/api/auth/me"))["csrf_token"]
    return client.post("/api" + path, json=payload or {}, headers={"X-CSRF-Token": csrf})


@pytest.fixture(autouse=True)
def no_external_services(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Integration tests must not send email or use real network connections")

    original_connect = socket.socket.connect
    socketpair_code = getattr(socket.socketpair, "__code__", None)

    def guarded_connect(sock, address):
        # Windows implements asyncio's internal socketpair with a loopback connect.
        # Permit only that stdlib caller, not arbitrary application localhost traffic.
        if socketpair_code is not None and sys._getframe(1).f_code is socketpair_code:
            return original_connect(sock, address)
        return blocked(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(smtplib.SMTP, "connect", blocked)


@pytest.fixture
def app_factory(tmp_path, monkeypatch):
    database_url = "sqlite:///" + (tmp_path / "integration.sqlite3").as_posix()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://testserver")
    monkeypatch.setenv("APP_BASE_URL", "https://testserver")
    monkeypatch.setenv("TRUSTED_HOSTS", "testserver")
    monkeypatch.setenv("SESSION_TTL_SECONDS", "604800")
    monkeypatch.setenv("EMAIL_FROM", "")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "")
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("SMTP_PASSWORD", "")
    monkeypatch.setenv("BREVO_API_KEY", "")
    monkeypatch.setenv("RESEND_API_KEY", "")
    monkeypatch.setenv("SENDGRID_API_KEY", "")
    # Import the implementation, not the CLI's eagerly constructed global app.
    module = importlib.import_module("investolingo_backend")
    applications = []

    def create():
        app = module.create_app()
        assert app.state.engine.url.database == str(tmp_path / "integration.sqlite3").replace("\\", "/")
        applications.append(app)
        return app

    yield create
    for app in applications:
        app.state.engine.dispose()


@pytest.fixture
def app(app_factory):
    return app_factory()


@pytest.fixture
def clients(app):
    with ExitStack() as stack:
        def create():
            return stack.enter_context(TestClient(app, base_url="https://testserver"))

        yield create


@pytest.fixture
def client(clients):
    return clients()


@pytest.fixture
def account(clients):
    sequence = count(1)

    def create(**overrides):
        client = clients()
        payload = {
            "name": "Integration Student",
            "email": f"student{next(sequence)}@example.com",
            "password": PASSWORD,
            "birth_date": "2000-01-01",
            **overrides,
        }
        data = ok(post(client, "/auth/register", payload))
        return client, data

    return create


@pytest.fixture
def educator(account, tmp_path):
    def create():
        client, data = account()
        ok(post(client, "/auth/verify-email", {"token": data["dev_token"]}))
        # Privileged fixture setup only; public registration must stay student-only.
        with sqlite3.connect(tmp_path / "integration.sqlite3") as db:
            result = db.execute("UPDATE users SET role = ? WHERE id = ?", ("educator_admin", data["user"]["id"]))
            assert result.rowcount == 1
        assert ok(client.get("/api/auth/me"))["user"]["role"] == "educator_admin"
        return client, data

    return create
