from datetime import date, timedelta

import pytest

from conftest import PASSWORD, denied, ok, post


@pytest.mark.parametrize("path", [
    "/me/dashboard", "/me/rewards", "/simulation", "/classes",
    "/me/export", "/me/subscription",
])
def test_anonymous_private_reads_denied(client, path):
    denied(client.get("/api" + path), (401, 403))


@pytest.mark.parametrize("path,payload", [
    ("/simulation/advance", {}),
    ("/simulation/trade", {"side": "buy", "ticker": "TEST", "qty": 1, "thesis": "A valid thesis for an unauthorized trade attempt."}),
    ("/simulation/reflect", {"text": "A sufficiently detailed reflection about risk and diversification."}),
    ("/me/onboarding", {"goal": "learn", "experience": "beginner"}),
    ("/me/subscription/mock", {"plan": "premium"}),
    ("/classes", {"name": "Unauthorized"}),
])
def test_anonymous_private_writes_denied_even_with_csrf(client, path, payload):
    denied(post(client, path, payload), (401, 403))


@pytest.mark.parametrize("path,payload", [
    ("/auth/register", {"name": "Student", "email": "csrf@example.com", "password": PASSWORD, "birth_date": "2000-01-01"}),
    ("/auth/login", {"email": "csrf@example.com", "password": PASSWORD}),
    ("/auth/forgot-password", {"email": "csrf@example.com"}),
    ("/auth/verify-email", {"token": "invalid"}),
    ("/auth/reset-password", {"token": "invalid", "password": PASSWORD}),
])
def test_public_auth_posts_require_csrf(client, path, payload):
    ok(client.get("/api/auth/me"))
    denied(client.post("/api" + path, json=payload), (403,))
    denied(client.post("/api" + path, json=payload, headers={"X-CSRF-Token": "forged"}), (403,))


def test_registration_session_and_logout(account, clients):
    client, registration = account()
    user = registration["user"]
    assert user["role"] == "student"
    assert user["email_verified"] is False
    assert user["plan"] == "free"
    assert registration["csrf_token"]
    assert not {"password", "password_hash"} & user.keys()
    assert ok(client.get("/api/auth/me"))["user"]["id"] == user["id"]
    replay = clients()
    replay.cookies.update(client.cookies)
    assert ok(post(client, "/auth/logout"))["ok"] is True
    assert ok(client.get("/api/auth/me"))["user"] is None
    denied(replay.get("/api/me/dashboard"), (401, 403))
    denied(post(client, "/auth/login", {"email": user["email"], "password": "wrong-password"}), (401, 403))
    logged_in = ok(post(client, "/auth/login", {"email": user["email"], "password": PASSWORD}))
    assert logged_in["user"]["id"] == user["id"]


def test_session_cookie_is_httponly(client):
    response = client.get("/api/auth/me")
    ok(response)
    cookies = response.headers.get_list("set-cookie")
    assert cookies, "Anonymous CSRF session must set a cookie"
    assert any("httponly" in cookie.lower() for cookie in cookies)
    assert any("samesite=" in cookie.lower() for cookie in cookies)


def test_csrf_is_bound_to_session_and_required_after_login(account):
    alice, _ = account()
    bob, _ = account()
    token = ok(bob.get("/api/auth/me"))["csrf_token"]
    for headers in ({}, {"X-CSRF-Token": token}, {"X-CSRF-Token": "forged"}):
        denied(alice.post("/api/auth/logout", json={}, headers=headers), (403,))
    assert ok(alice.get("/api/auth/me"))["user"] is not None


@pytest.mark.parametrize("path,payload", [
    ("/me/onboarding", {"goal": "Learn investing", "experience": "beginner"}),
    ("/me/delete", {"password": PASSWORD}),
    ("/lessons/investing-basics/complete", {"answer": 1}),
    ("/me/rewards/redeem", {"reward_id": "teal-notebook"}),
    ("/simulation/advance", {}),
    ("/simulation/trade", {"side": "buy", "ticker": "TEST", "qty": 1, "thesis": "A valid thesis for the CSRF test."}),
    ("/simulation/reflect", {"text": "I will diversify across several companies to reduce my exposure to a single sector."}),
    ("/classes", {"name": "Forged class"}),
    ("/classes/join", {"code": "NOTREAL"}),
    ("/classes/nonexistent/assignments", {"lesson_id": "investing-basics", "title": "Forged assignment"}),
    ("/classes/nonexistent/rewards", {"student_id": "nonexistent", "amount": 10, "reason": "Forged reward", "idempotency_key": "forged-key"}),
    ("/classes/nonexistent/remove", {"student_id": "nonexistent"}),
    ("/me/subscription/mock", {"plan": "premium"}),
])
def test_authenticated_mutations_require_csrf(account, path, payload):
    client, _ = account()
    for headers in ({}, {"X-CSRF-Token": "forged"}):
        response = client.post("/api" + path, json=payload, headers=headers)
        denied(response, (403,))
        assert "csrf" in response.json()["detail"].lower()


@pytest.mark.parametrize("birth_date", ["2019-01-01", "2999-01-01", "not-a-date"])
def test_age_gate_rejects_underage_future_and_invalid_dates(client, birth_date):
    denied(post(client, "/auth/register", {
        "name": "Too Young", "email": "young@example.com", "password": PASSWORD,
        "birth_date": birth_date,
    }), (400, 422))
    assert ok(client.get("/api/auth/me"))["user"] is None


def test_exact_thirteenth_birthday_is_allowed(account):
    today = date.today()
    try:
        birthday = today.replace(year=today.year - 13)
    except ValueError:
        birthday = today.replace(year=today.year - 13, day=28)
    _, data = account(birth_date=birthday.isoformat())
    assert data["user"]["role"] == "student"


def test_one_day_under_thirteen_is_rejected(client):
    today = date.today()
    try:
        birthday = today.replace(year=today.year - 13) + timedelta(days=1)
    except ValueError:
        birthday = date(today.year - 13, 3, 1)
    denied(post(client, "/auth/register", {
        "name": "Nearly Thirteen", "email": "nearly@example.com", "password": PASSWORD,
        "birth_date": birthday.isoformat(),
    }), (400, 422))


def test_public_registration_cannot_select_role_or_plan(client):
    response = post(client, "/auth/register", {
        "name": "Attacker", "email": "attacker@example.com", "password": PASSWORD,
        "birth_date": "2000-01-01", "role": "educator_admin", "plan": "premium",
        "email_verified": True, "xp": 100000,
    })
    if response.status_code in (400, 422):
        denied(response, (400, 422))
        return
    user = ok(response)["user"]
    assert user["role"] == "student"
    assert user["plan"] == "free"
    assert user["email_verified"] is False
    assert ok(client.get("/api/me/dashboard"))["xp"] == 0
    denied(post(client, "/classes", {"name": "Not an educator"}), (403,))


def test_duplicate_registration_does_not_replace_account(account, clients):
    original, data = account()
    denied(post(clients(), "/auth/register", {
        "name": "Replacement", "email": data["user"]["email"],
        "password": "Replacement-password-42!", "birth_date": "2000-01-01",
    }), (400, 409, 422))
    assert ok(original.get("/api/auth/me"))["user"] == data["user"]


def test_verification_tokens_are_single_use_and_purpose_bound(account):
    client, data = account()
    token = data.get("dev_token")
    assert token, "Development registration should expose a token for offline verification"
    denied(post(client, "/auth/reset-password", {"token": token, "password": PASSWORD}), (400, 401, 403, 422))
    denied(post(client, "/auth/verify-email", {"token": "invalid"}), (400, 401, 403, 422))
    assert ok(post(client, "/auth/verify-email", {"token": token}))["ok"] is True
    assert ok(client.get("/api/auth/me"))["user"]["email_verified"] is True
    denied(post(client, "/auth/verify-email", {"token": token}), (400, 401, 403, 409, 422))


def test_password_reset_is_single_use_revokes_sessions_and_changes_password(account, clients):
    client, data = account()
    email = data["user"]["email"]
    other_session = clients()
    ok(post(other_session, "/auth/login", {"email": email, "password": PASSWORD}))
    anonymous = clients()
    assert ok(post(anonymous, "/auth/forgot-password", {"email": "absent@example.com"}))["ok"] is True
    token = ok(post(anonymous, "/auth/forgot-password", {"email": email})).get("dev_token")
    assert token, "Development reset should expose an offline token"
    denied(post(anonymous, "/auth/verify-email", {"token": token}), (400, 401, 403, 422))
    new_password = "Changed-password-84!"
    assert ok(post(anonymous, "/auth/reset-password", {"token": token, "password": new_password}))["ok"] is True
    for session in (client, other_session):
        denied(session.get("/api/me/dashboard"), (401, 403))
    denied(post(anonymous, "/auth/reset-password", {"token": token, "password": PASSWORD}), (400, 401, 403, 409, 422))
    denied(post(anonymous, "/auth/login", {"email": email, "password": PASSWORD}), (401, 403))
    assert ok(post(anonymous, "/auth/login", {"email": email, "password": new_password}))["user"]["id"] == data["user"]["id"]


def test_registration_sends_email_through_resend(app_factory, monkeypatch):
    sent = []

    class Response:
        def raise_for_status(self):
            return None

    def send(url, **kwargs):
        sent.append((url, kwargs))
        return Response()

    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "notifications@example.com")
    monkeypatch.setattr("investolingo_backend.httpx.post", send)
    app = app_factory()
    from fastapi.testclient import TestClient
    with TestClient(app, base_url="https://testserver") as client:
        response = post(client, "/auth/register", {
            "name": "Email Student", "email": "delivery@example.com",
            "password": PASSWORD, "birth_date": "2000-01-01",
        })

    ok(response)
    assert sent[0][0] == "https://api.resend.com/emails"
    assert sent[0][1]["json"]["from"] == "notifications@example.com"
    assert sent[0][1]["json"]["to"] == ["delivery@example.com"]
    assert sent[0][1]["headers"]["Authorization"] == "Bearer re_test"
    assert "html" in sent[0][1]["json"]
    assert "🌿" in sent[0][1]["json"]["html"]
    assert "TradeQuest" in sent[0][1]["json"]["html"]


def test_registration_sends_email_through_brevo(app_factory, monkeypatch):
    sent = []

    class Response:
        def raise_for_status(self):
            return None

    def send(url, **kwargs):
        sent.append((url, kwargs))
        return Response()

    monkeypatch.setenv("BREVO_API_KEY", "xkeysib-test")
    monkeypatch.setenv("EMAIL_FROM", "notifications@example.com")
    monkeypatch.setattr("investolingo_backend.httpx.post", send)
    app = app_factory()
    from fastapi.testclient import TestClient
    with TestClient(app, base_url="https://testserver") as client:
        response = post(client, "/auth/register", {
            "name": "Brevo Student", "email": "brevo@example.com",
            "password": PASSWORD, "birth_date": "2000-01-01",
        })

    ok(response)
    assert sent[0][0] == "https://api.brevo.com/v3/smtp/email"
    assert sent[0][1]["json"]["to"] == [{"email": "brevo@example.com"}]
    assert sent[0][1]["headers"]["api-key"] == "xkeysib-test"
    assert "htmlContent" in sent[0][1]["json"]
    assert "🌿" in sent[0][1]["json"]["htmlContent"]
    assert "TradeQuest" in sent[0][1]["json"]["htmlContent"]
