from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from conftest import PASSWORD, denied, ok, post


def test_development_mock_plan_unlocks_lessons_and_never_bills(account):
    client, _ = account()
    assert ok(client.get("/api/plans"))["billing_enabled"] is False
    subscription = ok(client.get("/api/me/subscription"))
    assert subscription["plan"] == "free"
    assert subscription["mock_enabled"] is True
    ok(post(client, "/me/subscription/mock", {"plan": "premium"}))
    assert ok(client.get("/api/me/subscription"))["plan"] == "premium"
    premium = [item for item in ok(client.get("/api/lessons")) if item["premium"]]
    assert premium and all(not item["locked"] for item in premium)
    ok(post(client, "/me/subscription/mock", {"plan": "free"}))
    denied(post(client, f"/lessons/{premium[0]['id']}/complete", {"answer": 0}), (403,))
    denied(post(client, "/me/subscription/mock", {"plan": "educator_admin"}), (400, 422))
    assert ok(client.get("/api/me/subscription"))["plan"] == "free"


def test_production_forbids_mock_billing_and_hides_email_tokens(app_factory, monkeypatch):
    from investolingo_backend import Config

    # Exercise real production route/cookie behavior without PostgreSQL or SMTP.
    # Deployment validation is tested separately rather than weakened in backend code.
    config = replace(Config.load(), environment="production")
    monkeypatch.setattr(Config, "load", classmethod(lambda cls: config))
    with TestClient(app_factory(), base_url="https://testserver", headers={"Origin": "https://testserver"}) as client:
        registration = post(client, "/auth/register", {
            "name": "Production Student", "email": "production@example.com",
            "password": PASSWORD, "birth_date": "2000-01-01",
        })
        data = ok(registration)
        assert "dev_token" not in data
        cookies = registration.headers.get_list("set-cookie")
        assert any("secure" in cookie.lower() and "httponly" in cookie.lower() for cookie in cookies)
        subscription = ok(client.get("/api/me/subscription"))
        assert subscription["mock_enabled"] is False
        denied(post(client, "/me/subscription/mock", {"plan": "premium"}), (403, 404))
        assert ok(client.get("/api/me/subscription"))["plan"] == "free"
        reset = ok(post(client, "/auth/forgot-password", {"email": "production@example.com"}))
        assert "dev_token" not in reset
        assert ok(client.get("/api/plans"))["billing_enabled"] is False


def test_normal_production_configuration_rejects_sqlite(app_factory, monkeypatch):
    from investolingo_backend import Config

    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        Config.load()
