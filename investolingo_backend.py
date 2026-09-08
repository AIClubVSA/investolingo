"""Database-backed API. Every mutation is committed before its response is sent.

SQLite uses BEGIN IMMEDIATE; PostgreSQL uses a transaction advisory lock. This
deliberately serializes application transactions across workers, including reward
caps and JSON worlds. Replace with ordered row locks if throughput requires it.
"""

import copy
import hashlib
import logging
import os
import re
import secrets
import smtplib
import ssl
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Annotated, Literal
from urllib.parse import urlencode, urlsplit

import httpx
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import create_engine, delete, event, func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session as DBSession
from starlette.concurrency import run_in_threadpool

import aether_feedwatch as sim
from investolingo_content import CATALOG, LESSONS, MARKET_COURSES, PLANS
from investolingo_models import (
    Assignment, Base, Classroom, EmailToken, LearningProfile, Ledger, Membership,
    RateBucket, Redemption, Reflection, Session, User, World, WorldCheckpoint,
)

PASSWORDS = PasswordHasher()
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))
LOG = logging.getLogger("investolingo")
COOKIE = "investolingo_session"


def now():
    return int(time.time())


def today():
    return datetime.now(timezone.utc).date()


def uid():
    return str(uuid.uuid4())


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def fail(status, detail):
    raise HTTPException(status, detail)


@dataclass
class Config:
    environment: str
    database_url: str
    origins: list[str]
    hosts: list[str]
    base_url: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_ssl: bool
    brevo_api_key: str
    resend_api_key: str
    sendgrid_api_key: str
    session_seconds: int

    @property
    def production(self):
        return self.environment == "production"

    @classmethod
    def load(cls):
        if os.getenv("APP_ENV") and os.getenv("ENVIRONMENT") and os.environ["APP_ENV"] != os.environ["ENVIRONMENT"]:
            raise RuntimeError("APP_ENV and ENVIRONMENT must not conflict")
        vercel_env = os.getenv("VERCEL_ENV")
        environment = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", vercel_env or "development"))
        allowed = {"development", "test", "production", "preview"}
        if environment not in allowed:
            raise RuntimeError(f"APP_ENV/VERCEL_ENV must be one of {allowed}")
        production = environment == "production"
        is_vercel = vercel_env is not None
        vercel_url = os.getenv("VERCEL_URL", "").rstrip("/")
        vercel_origin = f"https://{vercel_url}" if vercel_url else ""
        database = os.getenv("DATABASE_URL", "sqlite:///./investolingo.db")
        if database.startswith("postgres://"):
            database = "postgresql+psycopg://" + database[len("postgres://"):]
        elif database.startswith("postgresql://"):
            database = "postgresql+psycopg://" + database[len("postgresql://"):]
        if not database.startswith(("sqlite:", "postgresql+psycopg:")):
            raise RuntimeError("DATABASE_URL must use SQLite or PostgreSQL (psycopg)")
        if is_vercel and not os.getenv("DATABASE_URL"):
            raise RuntimeError("Vercel deployments require DATABASE_URL (use Vercel Postgres or another PostgreSQL provider)")
        origins_env = os.getenv("ALLOWED_ORIGINS", "")
        if origins_env:
            origins = [x.strip().rstrip("/") for x in origins_env.split(",") if x.strip()]
        elif production:
            origins = [vercel_origin] if vercel_origin else []
        else:
            origins = [x for x in "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000".split(",") if x.strip()]
            if vercel_origin and vercel_origin not in origins:
                origins.append(vercel_origin)
        base = os.getenv("APP_BASE_URL", vercel_origin if vercel_origin else ("" if production else "http://localhost:5173")).rstrip("/")
        if base and base not in origins:
            origins.append(base)
        hosts_env = os.getenv("TRUSTED_HOSTS", "")
        if hosts_env:
            hosts = [x.strip() for x in hosts_env.split(",") if x.strip()]
        elif production:
            hosts = [vercel_url] if vercel_url else []
        else:
            hosts = ["localhost", "127.0.0.1", "testserver"]
            if vercel_url and vercel_url not in hosts:
                hosts.append(vercel_url)
        for origin in origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in ({"https"} if production else {"https", "http"}) or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username or "*" in origin:
                raise RuntimeError("ALLOWED_ORIGINS must contain exact trusted HTTP(S) origins; HTTPS required in production")
        config = cls(environment, database, origins, hosts, base,
                     os.getenv("SMTP_HOST", ""), int(os.getenv("SMTP_PORT", "587")),
                     os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", ""),
                     os.getenv("EMAIL_FROM") or os.getenv("RESEND_FROM_EMAIL") or os.getenv("SMTP_FROM", ""),
                     os.getenv("SMTP_SSL", "false").lower() == "true",
                     os.getenv("BREVO_API_KEY", ""),
                     os.getenv("RESEND_API_KEY", ""), os.getenv("SENDGRID_API_KEY", ""),
                     int(os.getenv("SESSION_TTL_SECONDS", "604800")))
        if not 300 <= config.session_seconds <= 2592000:
            raise RuntimeError("SESSION_TTL_SECONDS must be between 300 and 2592000")
        if production:
            if not os.getenv("DATABASE_URL") or not database.startswith("postgresql+psycopg:"):
                raise RuntimeError("Production requires an explicit PostgreSQL DATABASE_URL")
            if not origins or base not in origins or not hosts or any("*" in x for x in hosts):
                raise RuntimeError("Production requires ALLOWED_ORIGINS, matching APP_BASE_URL, and explicit TRUSTED_HOSTS")
            smtp_ready = all((config.smtp_host, config.smtp_user, config.smtp_password))
            api_ready = config.brevo_api_key or config.resend_api_key or config.sendgrid_api_key
            if not config.smtp_from or not (api_ready or smtp_ready):
                raise RuntimeError("Production requires EMAIL_FROM and a BREVO_API_KEY, RESEND_API_KEY, SENDGRID_API_KEY, or SMTP configuration")
        if config.smtp_host and not config.smtp_from:
            raise RuntimeError("SMTP_FROM is required when SMTP_HOST is set")
        return config


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Empty(Input):
    pass


def normalize_email(value):
    value = value.strip().lower()
    # These exact reserved addresses are the explicit local-demo API contract.
    if value in {"student@demo.investolingo.local", "admin@demo.investolingo.local"}:
        return value
    try:
        return validate_email(value, check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise ValueError("Invalid email address") from exc


Email = Annotated[str, Field(max_length=254), AfterValidator(normalize_email)]


class Credentials(Input):
    email: Email
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        if len(value) > 254:
            raise ValueError("Email is too long")
        return str(value).lower()

    # Passwords are never whitespace-normalized.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


def check_password(password):
    if len(password) < 12 or len(password) > 128 or len(set(password)) < 5:
        fail(422, "Password must be 12-128 characters with at least five distinct characters")


class Registration(Credentials):
    name: str = Field(min_length=1, max_length=80)
    birth_date: date

    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        if not value.strip():
            raise ValueError("Name is required")
        return value.strip()


class EmailInput(Input):
    email: Email


class TokenInput(Input):
    token: str = Field(min_length=20, max_length=200)


class ResetInput(TokenInput):
    password: str = Field(min_length=12, max_length=128)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class PasswordInput(Input):
    password: str = Field(min_length=1, max_length=128)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class OnboardingInput(Input):
    goal: str = Field(min_length=2, max_length=300)
    experience: str = Field(min_length=2, max_length=100)
    location: str | None = Field(default=None, min_length=2, max_length=100)
    age_band: str | None = Field(default=None, min_length=2, max_length=30)
    class_level: str | None = Field(default=None, min_length=1, max_length=50)
    school: str | None = Field(default=None, min_length=2, max_length=150)
    market: Literal["global", "us", "uk", "india"] | None = None


class AnswerInput(Input):
    answer: int = Field(strict=True, ge=0, le=20)


class RewardInput(Input):
    reward_id: str = Field(min_length=1, max_length=50)


class TradeInput(Input):
    side: Literal["buy", "sell"]
    ticker: str = Field(pattern=r"^[A-Z]{2,8}$")
    qty: int = Field(strict=True, gt=0, le=1000000)
    thesis: str = Field(min_length=10, max_length=2000)


class ReflectionInput(Input):
    text: str = Field(min_length=40, max_length=4000)

    @field_validator("text")
    @classmethod
    def meaningful(cls, value):
        words = re.findall(r"\w+", value.lower())
        if len(words) < 8 or len(set(words)) < 6:
            raise ValueError("Reflection needs at least eight words and six distinct words")
        return value


class ClassInput(Input):
    name: str = Field(min_length=2, max_length=100)


class JoinInput(Input):
    code: str = Field(min_length=6, max_length=16)


class AssignmentInput(Input):
    lesson_id: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=2, max_length=120)


class StudentInput(Input):
    student_id: str = Field(min_length=1, max_length=36)


class EducatorRewardInput(StudentInput):
    amount: int = Field(strict=True, ge=1, le=100)
    reason: str = Field(min_length=5, max_length=300)
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


class PlanInput(Input):
    plan: Literal["free", "premium"]


def lock_transaction(db):
    if db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    else:
        db.execute(text("SELECT pg_advisory_xact_lock(741209031)"))


def public_user(user):
    return {key: getattr(user, key) for key in ("id", "name", "email", "role", "email_verified", "onboarded", "plan")}


def verify_password(user, password):
    try:
        return PASSWORDS.verify(user.password_hash if user else DUMMY_HASH, password) and user is not None
    except (VerificationError, InvalidHashError):
        return False


@dataclass
class Context:
    db: DBSession
    session: Session | None
    user: User | None
    config: Config
    response: Response

    def authenticated(self, educator=False):
        if self.user is None:
            fail(401, "Sign in to continue")
        if educator and (self.user.role != "educator_admin" or not self.user.email_verified):
            fail(403, "A verified educator account is required")
        return self.user


def new_session(ctx, user=None):
    if ctx.session is not None:
        ctx.db.delete(ctx.session)
    token = secrets.token_urlsafe(32)
    ttl = ctx.config.session_seconds if user else 3600
    ctx.session = Session(id=digest(token), user_id=user.id if user else None,
                          csrf=secrets.token_urlsafe(32), expires_at=now() + ttl)
    ctx.db.add(ctx.session)
    ctx.user = user
    ctx.response.set_cookie(COOKIE, token, max_age=ttl, httponly=True,
                            secure=ctx.config.production, samesite="lax", path="/")
    return {"user": public_user(user) if user else None, "csrf_token": ctx.session.csrf}


def _build_email_body(user_name, purpose, link, token):
    action = "verify your email" if purpose == "verify" else "reset your password"
    accent = "#087b70"
    navy = "#20334b"
    muted = "#59677b"
    mint = "#e3f4ed"
    paper = "#ffffff"
    border = "#dce2eb"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>TradeQuest</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=DM+Sans:wght@400;500;700&display=swap');
</style>
</head>
<body style="margin:0;padding:0;background:#f5f7fb;font-family:'DM Sans',Arial,sans-serif;color:{navy};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f7fb;">
    <tr><td align="center" style="padding:40px 16px;">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;width:100%;background:{paper};border-radius:20px;border:1px solid {border};overflow:hidden;">
        <!-- Header -->
        <tr><td style="padding:36px 32px 24px;text-align:center;">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;">
            <tr>
              <td style="width:44px;height:44px;background:{accent};border-radius:12px;text-align:center;vertical-align:middle;transform:rotate(-5deg);">
                <span style="color:#fff;font-size:22px;line-height:44px;display:block;">🌿</span>
              </td>
              <td style="padding-left:12px;font-family:'Nunito',Arial Black,sans-serif;font-size:22px;font-weight:900;color:{navy};letter-spacing:-0.5px;">
                TradeQuest
              </td>
            </tr>
          </table>
        </td></tr>
        <!-- Eyebrow -->
        <tr><td style="padding:0 32px 8px;text-align:center;font-size:11px;letter-spacing:1.8px;font-weight:800;text-transform:uppercase;color:{accent};font-family:'Nunito',Arial,sans-serif;">
          Small lessons. Bigger perspective.
        </td></tr>
        <!-- Title -->
        <tr><td style="padding:0 32px 16px;text-align:center;font-family:'Nunito',Arial,sans-serif;font-size:26px;font-weight:900;color:{navy};letter-spacing:-1px;line-height:1.2;">
          {action.capitalize()}
        </td></tr>
        <!-- Body -->
        <tr><td style="padding:0 32px 28px;font-size:15px;line-height:1.75;color:{muted};">
          <p style="margin:0 0 18px 0;">Hi {user_name},</p>
          <p style="margin:0 0 18px 0;">Tap the button below to {action}.</p>
          <p style="margin:0 0 24px 0;text-align:center;">
            <a href="{link}" style="display:inline-block;padding:14px 28px;background:{accent};color:#fff;text-decoration:none;border-radius:12px;font-weight:700;font-size:15px;font-family:'Nunito',Arial,sans-serif;box-shadow:0 3px 0 #075f57;">{action.capitalize()}</a>
          </p>
          <p style="margin:0 0 12px 0;font-size:13px;color:{muted};">Or paste this one-time token into the app:</p>
          <p style="margin:0;padding:14px 18px;background:{mint};border-radius:10px;font-family:monospace;font-size:14px;color:#196155;font-weight:700;word-break:break-all;text-align:center;">
            {token}
          </p>
        </td></tr>
        <!-- Divider -->
        <tr><td style="padding:0 32px;"><hr style="border:0;border-top:1px solid {border};margin:0;" /></td></tr>
        <!-- Footer -->
        <tr><td style="padding:20px 32px 36px;text-align:center;font-size:12px;color:#9aa3b2;line-height:1.6;">
          Didn’t request this? You can safely ignore it.<br />
          <span style="color:{muted};font-weight:700;">TradeQuest</span> — Learn money, grow confidence.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def issue_email(ctx, user, purpose):
    ctx.db.execute(delete(EmailToken).where(EmailToken.user_id == user.id, EmailToken.purpose == purpose))
    token = secrets.token_urlsafe(32)
    ctx.db.add(EmailToken(id=digest(token), user_id=user.id, purpose=purpose,
                         expires_at=now() + (86400 if purpose == "verify" else 1800)))
    config = ctx.config
    subject = "TradeQuest: " + ("verify your email" if purpose == "verify" else "reset your password")
    # Fragment tokens stay out of access logs and Referer headers.
    link = config.base_url + "/#" + urlencode({"action": "verify-email" if purpose == "verify" else "reset-password", "token": token})
    action = "verify your email" if purpose == "verify" else "reset your password"
    text_content = f"Open TradeQuest to {action}:\n{link}\n\nOr enter this one-time token in the app:\n{token}\n\nIgnore this message if you did not request it."
    html_body = _build_email_body(user.name, purpose, link, token)
    if config.brevo_api_key or config.resend_api_key or config.sendgrid_api_key or config.smtp_host:
        try:
            if config.brevo_api_key:
                response = httpx.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers={
                        "api-key": config.brevo_api_key,
                        "accept": "application/json",
                        "content-type": "application/json",
                    },
                    json={
                        "sender": {"email": config.smtp_from},
                        "to": [{"email": user.email}],
                        "subject": subject,
                        "htmlContent": html_body,
                        "textContent": text_content,
                    },
                    timeout=10,
                )
                response.raise_for_status()
            elif config.resend_api_key:
                response = httpx.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {config.resend_api_key}"},
                    json={"from": config.smtp_from, "to": [user.email], "subject": subject, "html": html_body, "text": text_content},
                    timeout=10,
                )
                response.raise_for_status()
            elif config.sendgrid_api_key:
                response = httpx.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={"Authorization": f"Bearer {config.sendgrid_api_key}"},
                    json={
                        "personalizations": [{"to": [{"email": user.email}]}],
                        "from": {"email": config.smtp_from},
                        "subject": subject,
                        "content": [
                            {"type": "text/plain", "value": text_content},
                            {"type": "text/html", "value": html_body},
                        ],
                    },
                    timeout=10,
                )
                response.raise_for_status()
            else:
                message = EmailMessage()
                message["From"] = config.smtp_from
                message["To"] = user.email
                message["Subject"] = subject
                message.set_content(text_content)
                message.add_alternative(html_body, subtype="html")
                client = smtplib.SMTP_SSL if config.smtp_ssl else smtplib.SMTP
                kwargs = {"context": ssl.create_default_context()} if config.smtp_ssl else {}
                with client(config.smtp_host, config.smtp_port, timeout=10, **kwargs) as server:
                    if not config.smtp_ssl:
                        server.starttls(context=ssl.create_default_context())
                    if config.smtp_user:
                        server.login(config.smtp_user, config.smtp_password)
                    server.send_message(message)
        except (OSError, smtplib.SMTPException, httpx.HTTPError):
            LOG.exception("Email delivery failed")
            fail(503, "Email delivery is temporarily unavailable; please retry")
    return {"dev_token": token} if not config.production else {}


def ledger_for(db, user_id):
    return list(db.scalars(select(Ledger).where(Ledger.user_id == user_id).order_by(Ledger.created_at.desc(), Ledger.id)))


def profile_for(db, user_id):
    profile = db.get(LearningProfile, user_id)
    fields = ("location", "age_band", "class_level", "school", "market")
    return {field: getattr(profile, field) if profile else None for field in fields}


def progress(db, user):
    entries = ledger_for(db, user.id)
    xp = sum(entry.amount for entry in entries)
    level = xp // 250 + 1
    days = {datetime.fromtimestamp(e.created_at, timezone.utc).date() for e in entries if e.kind in {"lesson", "reflection"}}
    cursor = today() if today() in days else today() - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    completed = sum(e.kind == "lesson" for e in entries)
    badges = []
    if completed:
        badges.append(dict(id="first-lesson", name="First chapter", description="Complete your first lesson."))
    if completed >= 4:
        badges.append(dict(id="core-reader", name="Core reader", description="Complete four lessons."))
    if streak >= 3:
        badges.append(dict(id="three-day-streak", name="Steady learner", description="Learn on three consecutive UTC days."))
    return dict(xp=xp, level=level, level_name=["Curious Beginner", "Growing Learner", "Thoughtful Investor", "Market Scholar"][min(level - 1, 3)],
                next_level_xp=level * 250, streak=streak, completed_lessons=completed, badges=badges,
                 onboarded=user.onboarded, goal=user.goal, experience=user.experience,
                 profile=profile_for(db, user.id))


def award(ctx, user, key, amount, reason, kind, source, actor_id=None):
    if ctx.db.scalar(select(Ledger).where(Ledger.award_key == key)):
        return 0
    ctx.db.add(Ledger(id=uid(), user_id=user.id, award_key=key, amount=amount,
                      reason=reason, kind=kind, source=source, actor_id=actor_id, created_at=now()))
    ctx.db.flush()
    return amount


def lesson_by_id(lesson_id):
    lesson = next((x for x in LESSONS if x["id"] == lesson_id), None)
    if lesson is None:
        fail(404, "Lesson not found")
    return lesson


def world_for(ctx):
    user = ctx.authenticated()
    world = ctx.db.get(World, user.id)
    if world is None:
        state = sim.new_state(secrets.randbits(53), today().isoformat())
        sim.run_day(state, offline=True, quiet=True)
        if sim.check_invariants(state):
            fail(409, "Simulation initialization failed")
        world = World(user_id=user.id, state=state)
        ctx.db.add(world)
        ctx.db.flush()
    return world


def public_world(state, can_rollback=False):
    portfolio = state["portfolio"]
    return dict(
        summary={**{key: state[key] for key in ("sim_day", "prices", "last_return", "resources")},
                 "sim_date": (date.fromisoformat(state["start_date"]) + timedelta(days=state["sim_day"] - 1)).isoformat()},
        companies=[dict(ticker=t, name=c[0], region=c[1]) for t, c in sim.COMPANIES.items()],
        events=[{key: event[key] for key in ("id", "headline", "report", "category", "date", "region", "severity")} for event in reversed(state["events"][-100:])],
        portfolio={**portfolio, "value": round(portfolio["cash"] + sum(qty * state["prices"][t] for t, qty in portfolio["holdings"].items()), 2)},
        can_rollback=can_rollback,
    )


def owned_class(ctx, class_id):
    user = ctx.authenticated(educator=True)
    classroom = ctx.db.get(Classroom, class_id)
    if classroom is None or classroom.owner_id != user.id:
        fail(404, "Class not found")
    return classroom


def client_ip(request):
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def check_rate(engine, ip, auth_path, email):
    timestamp = now()
    buckets = [("ip:" + ip, "all", 60, 180)]
    if auth_path:
        buckets.append(("ip:" + ip, "auth", 900, 30))
        if email:
            try:
                email = normalize_email(email) if len(email) <= 254 else None
            except ValueError:
                email = None
            if email:
                buckets.append(("email:" + email, "auth", 900, 20))
    # Counters survive failed validation, failed passwords and CSRF rejection.
    with DBSession(engine) as db:
        lock_transaction(db)
        db.execute(delete(RateBucket).where(RateBucket.expires_at <= timestamp))
        exceeded = False
        for identity, label, period, limit in buckets:
            bucket_id = digest(f"{identity}:{label}:{timestamp // period}")
            bucket = db.get(RateBucket, bucket_id)
            if bucket is None:
                bucket = RateBucket(id=bucket_id, count=0, expires_at=(timestamp // period + 1) * period)
                db.add(bucket)
            bucket.count = min(bucket.count + 1, limit + 1)
            if bucket.count > limit:
                # Blocked clients must not allocate buckets for new identities.
                exceeded = True
                break
        db.commit()
    return exceeded


class BodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH", "DELETE"}:
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 65536:
                return await JSONResponse({"detail": "Request body exceeds 64 KiB"}, status_code=413)(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app():
    config = Config.load()
    engine = create_engine(config.database_url, pool_pre_ping=True,
                           connect_args={"check_same_thread": False, "timeout": 30} if config.database_url.startswith("sqlite:") else {})
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def sqlite_settings(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=30000")
            connection.execute("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(engine)
    app = FastAPI(title="TradeQuest API", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine = engine
    app.state.config = config

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({"detail": "Invalid request: " + "; ".join(".".join(str(x) for x in e["loc"]) + ": " + e["msg"] for e in exc.errors())}, status_code=422)

    @app.exception_handler(IntegrityError)
    async def conflict(request, exc):
        return JSONResponse({"detail": "This operation conflicts with existing data"}, status_code=409)

    @app.exception_handler(OperationalError)
    async def unavailable(request, exc):
        return JSONResponse({"detail": "Database temporarily unavailable; retry shortly"}, status_code=503)

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        LOG.error("Unhandled API error: %s", type(exc).__name__)
        return JSONResponse({"detail": "Internal server error"}, status_code=500)

    @app.middleware("http")
    async def browser_security(request, call_next):
        try:
            host = urlsplit("//" + request.headers.get("host", ""))
            valid_host = host.hostname in config.hosts and not (host.username or host.path or host.query or host.fragment)
            host.port  # Reject malformed ports as well as malformed hostnames.
        except ValueError:
            valid_host = False
        if not valid_host:
            return JSONResponse({"detail": "Host is not allowed"}, status_code=400)
        if request.url.path.startswith("/api"):
            auth_path = request.url.path.startswith("/api/auth/") and request.method == "POST"
            email = None
            if auth_path:
                try:
                    body = await request.json()
                    if isinstance(body, dict) and isinstance(body.get("email"), str):
                        email = body["email"]
                except (ValueError, UnicodeDecodeError):
                    pass
            ip = client_ip(request)
            try:
                exceeded = await run_in_threadpool(check_rate, engine, ip, auth_path, email)
            except OperationalError:
                return JSONResponse({"detail": "Database temporarily unavailable"}, status_code=503)
            if exceeded:
                return JSONResponse({"detail": "Too many requests; try again later"}, status_code=429, headers={"Retry-After": "900"})
        origin = request.headers.get("origin")
        if origin is not None and origin not in config.origins:
            return JSONResponse({"detail": "Origin is not allowed"}, status_code=403)
        if request.method == "POST" and config.production and not origin:
            return JSONResponse({"detail": "Origin header is required"}, status_code=403)
        if request.method == "POST" and request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
            return JSONResponse({"detail": "Content-Type must be application/json"}, status_code=415)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if config.production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=config.origins, allow_credentials=True,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-CSRF-Token"])

    def context(request: Request, response: Response):
        timestamp = now()
        with DBSession(engine, expire_on_commit=False) as db:
            lock_transaction(db)
            try:
                db.execute(delete(Session).where(Session.expires_at <= timestamp))
                db.execute(delete(EmailToken).where(EmailToken.expires_at <= timestamp))
                raw = request.cookies.get(COOKIE, "")
                session = db.get(Session, digest(raw)) if raw and len(raw) <= 200 else None
                user = db.get(User, session.user_id) if session and session.user_id else None
                ctx = Context(db, session, user, config, response)
                if request.method == "POST":
                    csrf = request.headers.get("x-csrf-token", "")
                    if not session or not secrets.compare_digest(csrf.encode(), session.csrf.encode()):
                        fail(403, "Invalid or expired CSRF token; reload your session")
                yield ctx
                db.commit()
            except BaseException:
                db.rollback()
                raise

    Ctx = Annotated[Context, Depends(context, scope="function")]

    @app.get("/api/auth/me")
    def me(ctx: Ctx):
        if ctx.session is None:
            return new_session(ctx)
        return {"user": public_user(ctx.user) if ctx.user else None, "csrf_token": ctx.session.csrf}

    @app.post("/api/auth/register")
    def register(body: Registration, ctx: Ctx):
        check_password(body.password)
        if body.email.endswith("@demo.investolingo.local"):
            fail(422, "Demo addresses are reserved for CLI seeding")
        age = today().year - body.birth_date.year - ((today().month, today().day) < (body.birth_date.month, body.birth_date.day))
        if age < 13 or age > 120:
            fail(422, "You must be at least 13 and provide a valid birth date")
        if ctx.db.scalar(select(User).where(User.email == body.email)):
            fail(409, "An account with that email already exists")
        user = User(id=uid(), name=body.name, email=str(body.email), password_hash=PASSWORDS.hash(body.password),
                    birth_date=body.birth_date.isoformat(), created_at=now())
        ctx.db.add(user)
        ctx.db.flush()
        return {**new_session(ctx, user), **issue_email(ctx, user, "verify")}

    @app.post("/api/auth/login")
    def login(body: Credentials, ctx: Ctx):
        user = ctx.db.scalar(select(User).where(User.email == body.email))
        if not verify_password(user, body.password):
            fail(401, "Invalid email or password")
        if PASSWORDS.check_needs_rehash(user.password_hash):
            user.password_hash = PASSWORDS.hash(body.password)
        return new_session(ctx, user)

    @app.post("/api/auth/logout")
    def logout(body: Empty, ctx: Ctx):
        ctx.db.delete(ctx.session)
        ctx.response.delete_cookie(COOKIE, path="/", secure=config.production, httponly=True, samesite="lax")
        return {"ok": True}

    @app.post("/api/auth/verify-email")
    def verify_email(body: TokenInput, ctx: Ctx):
        token = ctx.db.get(EmailToken, digest(body.token))
        if token is None or token.purpose != "verify" or token.expires_at <= now():
            fail(400, "Invalid or expired verification token")
        user = ctx.db.get(User, token.user_id)
        user.email_verified = True
        ctx.db.delete(token)
        return {"ok": True}

    @app.post("/api/auth/forgot-password")
    def forgot_password(body: EmailInput, ctx: Ctx):
        user = ctx.db.scalar(select(User).where(User.email == str(body.email).lower()))
        result = {"ok": True}
        if user:
            # Successful email recovery proves mailbox ownership as well.
            try:
                with ctx.db.begin_nested():
                    result.update(issue_email(ctx, user, "reset"))
            except HTTPException as exc:
                if exc.status_code != 503:
                    raise
                # Do not disclose whether an account exists on mail-provider failure.
                if not config.production:
                    raise
        return result

    @app.post("/api/auth/reset-password")
    def reset_password(body: ResetInput, ctx: Ctx):
        check_password(body.password)
        token = ctx.db.get(EmailToken, digest(body.token))
        if token is None or token.purpose != "reset" or token.expires_at <= now():
            fail(400, "Invalid or expired recovery token")
        user = ctx.db.get(User, token.user_id)
        user.password_hash = PASSWORDS.hash(body.password)
        user.email_verified = True
        ctx.db.execute(delete(EmailToken).where(EmailToken.user_id == user.id))
        ctx.db.execute(delete(Session).where(Session.user_id == user.id))
        if ctx.user and ctx.user.id == user.id:
            ctx.response.delete_cookie(COOKIE, path="/", secure=config.production, httponly=True, samesite="lax")
        return {"ok": True}

    @app.post("/api/me/onboarding")
    def onboarding(body: OnboardingInput, ctx: Ctx):
        user = ctx.authenticated()
        user.goal, user.experience, user.onboarded = body.goal, body.experience, True
        profile = ctx.db.get(LearningProfile, user.id)
        if profile is None:
            profile = LearningProfile(user_id=user.id)
            ctx.db.add(profile)
        for field in ("location", "age_band", "class_level", "school", "market"):
            if field in body.model_fields_set:
                setattr(profile, field, getattr(body, field))
        return {"ok": True, "profile": profile_for(ctx.db, user.id)}

    @app.get("/api/me/dashboard")
    def dashboard(ctx: Ctx):
        return progress(ctx.db, ctx.authenticated())

    @app.get("/api/lessons")
    def lessons(ctx: Ctx):
        user = ctx.authenticated()
        completed = {e.source for e in ledger_for(ctx.db, user.id) if e.kind == "lesson"}
        result = []
        for lesson in LESSONS:
            locked = lesson["premium"] and user.plan != "premium"
            item = {k: v for k, v in lesson.items() if k != "answer"}
            if locked:
                item.update(content="Upgrade to premium to open this lesson.", question="", options=[])
            result.append({**item, "completed": lesson["id"] in completed, "locked": locked})
        return result

    @app.get("/api/courses")
    def courses(ctx: Ctx, market: Literal["global", "us", "uk", "india"] | None = None):
        user = ctx.authenticated()
        completed = {e.source for e in ledger_for(ctx.db, user.id) if e.kind == "lesson"}
        result = []
        for course in MARKET_COURSES:
            if market is not None and course["market"] != market:
                continue
            completed_count = len(completed.intersection(course["lesson_ids"]))
            total = len(course["lesson_ids"])
            result.append({
                **course,
                "progress": {
                    "completed": completed_count,
                    "total": total,
                    "percent": round(completed_count / total * 100) if total else 0,
                },
                "completed": completed_count == total,
            })
        return result

    @app.post("/api/lessons/{lesson_id}/complete")
    def complete_lesson(lesson_id: str, body: AnswerInput, ctx: Ctx):
        user = ctx.authenticated()
        lesson = lesson_by_id(lesson_id)
        if lesson["premium"] and user.plan != "premium":
            fail(403, "Premium plan required")
        if body.answer >= len(lesson["options"]):
            fail(422, "Answer is outside the available options")
        if body.answer != lesson["answer"]:
            return {"correct": False, "xp_awarded": 0, "message": "Not quite. Revisit the lesson and try again."}
        amount = award(ctx, user, f"lesson:{user.id}:{lesson_id}", lesson["xp"], f"Completed {lesson['title']}", "lesson", lesson_id)
        return {"correct": True, "xp_awarded": amount, "message": "Lesson complete!" if amount else "Already completed; no duplicate XP awarded."}

    @app.get("/api/me/rewards")
    def rewards(ctx: Ctx):
        user = ctx.authenticated()
        redeemed = list(ctx.db.scalars(select(Redemption).where(Redemption.user_id == user.id)))
        owned = {r.reward_id for r in redeemed}
        data = progress(ctx.db, user)
        return {**data, "credits": data["xp"] - sum(r.cost for r in redeemed),
                "ledger": [dict(id=e.id, amount=e.amount, reason=e.reason, created_at=datetime.fromtimestamp(e.created_at, timezone.utc).isoformat()) for e in ledger_for(ctx.db, user.id)],
                "catalog": [{**r, "owned": r["id"] in owned} for r in CATALOG]}

    @app.post("/api/me/rewards/redeem")
    def redeem(body: RewardInput, ctx: Ctx):
        user = ctx.authenticated()
        reward = next((r for r in CATALOG if r["id"] == body.reward_id), None)
        if reward is None:
            fail(404, "Reward not found")
        redeemed = list(ctx.db.scalars(select(Redemption).where(Redemption.user_id == user.id)))
        if any(r.reward_id == body.reward_id for r in redeemed):
            return {"ok": True}
        credits = sum(e.amount for e in ledger_for(ctx.db, user.id)) - sum(r.cost for r in redeemed)
        if credits < reward["cost"]:
            fail(409, "Not enough cosmetic credits")
        ctx.db.add(Redemption(id=uid(), user_id=user.id, reward_id=reward["id"], cost=reward["cost"], created_at=now()))
        return {"ok": True}

    @app.get("/api/simulation")
    def simulation(ctx: Ctx):
        world = world_for(ctx)
        return public_world(world.state, ctx.db.get(WorldCheckpoint, world.user_id) is not None)

    @app.get("/api/simulation/history")
    def simulation_history(
        ctx: Ctx,
        ticker: Annotated[str, Query(min_length=2, max_length=8, pattern=r"^[A-Za-z]{2,8}$")],
        range_name: Annotated[Literal["1d", "1w", "1m", "1y", "5y", "10y"], Query(alias="range")] = "1m",
    ):
        state = world_for(ctx).state
        ticker = ticker.upper()
        if ticker not in sim.COMPANIES:
            fail(404, "Ticker not found")
        days = {"1d": 1, "1w": 7, "1m": 30, "1y": 365, "5y": 1825, "10y": 3650}[range_name]
        entries = state.get("history", [])[-days:]
        start = date.fromisoformat(state["start_date"])
        return {
            "ticker": ticker,
            "range": range_name,
            "points": [
                {
                    "day": entry["day"],
                    "date": (start + timedelta(days=entry["day"] - 1)).isoformat(),
                    "price": entry["prices"][ticker],
                }
                for entry in entries
            ],
        }

    @app.post("/api/simulation/advance")
    def advance(body: Empty, ctx: Ctx):
        world = world_for(ctx)
        state = copy.deepcopy(world.state)
        if state["sim_day"] >= 36500:
            fail(409, "Simulation day limit reached")
        checkpoint = ctx.db.get(WorldCheckpoint, world.user_id)
        if checkpoint is None:
            checkpoint = WorldCheckpoint(user_id=world.user_id, state=copy.deepcopy(world.state), created_at=now())
            ctx.db.add(checkpoint)
        else:
            checkpoint.state = copy.deepcopy(world.state)
            checkpoint.created_at = now()
        sim.run_day(state, offline=True, quiet=True)
        if sim.check_invariants(state):
            fail(409, "Simulation consistency check failed; no change saved")
        world.state = state
        return {"ok": True, "can_rollback": True}

    @app.post("/api/simulation/rollback")
    def rollback(body: Empty, ctx: Ctx):
        world = world_for(ctx)
        checkpoint = ctx.db.get(WorldCheckpoint, world.user_id)
        if checkpoint is None:
            fail(409, "No simulation advance is available to roll back")
        world.state = copy.deepcopy(checkpoint.state)
        ctx.db.delete(checkpoint)
        return {"ok": True, "can_rollback": False}

    @app.post("/api/simulation/trade")
    def trade(body: TradeInput, ctx: Ctx):
        world = world_for(ctx)
        state = copy.deepcopy(world.state)
        try:
            message = sim.trade(state, body.side, body.ticker, body.qty)
        except ValueError as exc:
            fail(400, str(exc))
        state["portfolio"]["trades"][-1]["thesis"] = body.thesis
        if sim.check_invariants(state):
            fail(409, "Simulation consistency check failed; no change saved")
        world.state = state
        return {"message": message}

    @app.post("/api/simulation/reflect")
    def reflect(body: ReflectionInput, ctx: Ctx):
        user = ctx.authenticated()
        day = today().isoformat()
        amount = award(ctx, user, f"reflection:{user.id}:{day}", 25, "Daily simulation reflection", "reflection", day)
        if amount:
            ctx.db.add(Reflection(id=uid(), user_id=user.id, day=day, text=body.text))
        return {"xp_awarded": amount, "message": "Reflection saved." if amount else "You have already reflected today (UTC)."}

    @app.get("/api/classes")
    def classes(ctx: Ctx):
        user = ctx.authenticated()
        query = select(Classroom)
        if user.role == "educator_admin":
            query = query.where(Classroom.owner_id == user.id)
        else:
            query = query.join(Membership).where(Membership.user_id == user.id)
        return [dict(id=c.id, name=c.name, code=c.code, member_count=ctx.db.scalar(select(func.count()).select_from(Membership).where(Membership.class_id == c.id))) for c in ctx.db.scalars(query.order_by(Classroom.name))]

    @app.post("/api/classes")
    def create_class(body: ClassInput, ctx: Ctx):
        user = ctx.authenticated(educator=True)
        if ctx.db.scalar(select(func.count()).select_from(Classroom).where(Classroom.owner_id == user.id)) >= 50:
            fail(409, "Class limit reached")
        classroom = Classroom(id=uid(), owner_id=user.id, name=body.name, code=secrets.token_hex(5).upper())
        ctx.db.add(classroom)
        return dict(id=classroom.id, name=classroom.name, code=classroom.code)

    @app.post("/api/classes/join")
    def join_class(body: JoinInput, ctx: Ctx):
        user = ctx.authenticated()
        if user.role != "student":
            fail(403, "Only student accounts can join classes")
        classroom = ctx.db.scalar(select(Classroom).where(Classroom.code == body.code.upper()))
        if classroom is None:
            fail(404, "Class code not found")
        if ctx.db.get(Membership, (classroom.id, user.id)):
            return {"ok": True}
        if ctx.db.scalar(select(func.count()).select_from(Membership).where(Membership.class_id == classroom.id)) >= 500:
            fail(409, "Class is full")
        if ctx.db.scalar(select(func.count()).select_from(Membership).where(Membership.user_id == user.id)) >= 50:
            fail(409, "Membership limit reached")
        ctx.db.add(Membership(class_id=classroom.id, user_id=user.id))
        return {"ok": True}

    @app.get("/api/classes/{class_id}")
    def class_detail(class_id: str, ctx: Ctx):
        classroom = owned_class(ctx, class_id)
        students = list(ctx.db.scalars(select(User).join(Membership).where(Membership.class_id == class_id).order_by(User.name)))
        return dict(id=classroom.id, name=classroom.name, code=classroom.code,
                    students=[dict(id=u.id, name=u.name, **{k: v for k, v in progress(ctx.db, u).items() if k in {"xp", "completed_lessons"}}) for u in students],
                    assignments=[dict(id=a.id, title=a.title, lesson_id=a.lesson_id) for a in ctx.db.scalars(select(Assignment).where(Assignment.class_id == class_id))])

    @app.post("/api/classes/{class_id}/assignments")
    def assign(class_id: str, body: AssignmentInput, ctx: Ctx):
        owned_class(ctx, class_id)
        lesson = lesson_by_id(body.lesson_id)
        if lesson["premium"] and ctx.user.plan != "premium":
            fail(403, "Premium plan required to assign this lesson")
        existing = ctx.db.scalar(select(Assignment).where(Assignment.class_id == class_id, Assignment.lesson_id == body.lesson_id))
        if existing:
            existing.title = body.title
        else:
            ctx.db.add(Assignment(id=uid(), class_id=class_id, lesson_id=body.lesson_id, title=body.title))
        return {"ok": True}

    @app.post("/api/classes/{class_id}/rewards")
    def educator_reward(class_id: str, body: EducatorRewardInput, ctx: Ctx):
        owned_class(ctx, class_id)
        if ctx.db.get(Membership, (class_id, body.student_id)) is None:
            fail(404, "Student is not in this class")
        key = f"educator:{ctx.user.id}:{body.idempotency_key}"
        previous = ctx.db.scalar(select(Ledger).where(Ledger.award_key == key))
        if previous:
            if (previous.user_id, previous.amount, previous.reason, previous.source) != (body.student_id, body.amount, body.reason, class_id):
                fail(409, "Idempotency key was already used for a different reward")
            return {"ok": True}
        day_start = int(datetime.combine(today(), datetime.min.time(), timezone.utc).timestamp())
        total = ctx.db.scalar(select(func.coalesce(func.sum(Ledger.amount), 0)).where(Ledger.user_id == body.student_id, Ledger.kind == "educator", Ledger.created_at >= day_start))
        if total + body.amount > 100:
            fail(409, "Student has reached the daily educator reward limit of 100 XP (UTC)")
        student = ctx.db.get(User, body.student_id)
        award(ctx, student, key, body.amount, body.reason, "educator", class_id, ctx.user.id)
        return {"ok": True}

    @app.post("/api/classes/{class_id}/remove")
    def remove_student(class_id: str, body: StudentInput, ctx: Ctx):
        owned_class(ctx, class_id)
        membership = ctx.db.get(Membership, (class_id, body.student_id))
        if membership:
            ctx.db.delete(membership)
        return {"ok": True}

    @app.get("/api/plans")
    def plans(ctx: Ctx):
        return PLANS

    @app.get("/api/me/subscription")
    def subscription(ctx: Ctx):
        user = ctx.authenticated()
        return {"plan": user.plan, "status": "active" if user.plan == "free" else "mock", "mock_enabled": not config.production}

    @app.post("/api/me/subscription/mock")
    def mock_subscription(body: PlanInput, ctx: Ctx):
        user = ctx.authenticated()
        if config.production:
            fail(403, "Mock subscriptions are disabled in production")
        user.plan = body.plan
        return {"ok": True}

    @app.get("/api/me/export")
    def export(ctx: Ctx):
        user = ctx.authenticated()
        world = ctx.db.get(World, user.id)
        return {"user": {**public_user(user), "birth_date": user.birth_date, "created_at": datetime.fromtimestamp(user.created_at, timezone.utc).isoformat()},
                "profile": profile_for(ctx.db, user.id),
                "dashboard": progress(ctx.db, user), "rewards": rewards(ctx),
                "reflections": [dict(day=r.day, text=r.text) for r in ctx.db.scalars(select(Reflection).where(Reflection.user_id == user.id))],
                "redemptions": [dict(reward_id=r.reward_id, cost=r.cost, created_at=r.created_at) for r in ctx.db.scalars(select(Redemption).where(Redemption.user_id == user.id))],
                "simulation": public_world(world.state, ctx.db.get(WorldCheckpoint, user.id) is not None) if world else None,
                "classes": classes(ctx),
                "assignments": [dict(id=a.id, class_id=a.class_id, lesson_id=a.lesson_id, title=a.title) for a in ctx.db.scalars(select(Assignment).join(Classroom).where(Classroom.owner_id == user.id))]}

    @app.post("/api/me/delete")
    def delete_account(body: PasswordInput, ctx: Ctx):
        user = ctx.authenticated()
        if not verify_password(user, body.password):
            fail(401, "Invalid password")
        ctx.db.delete(user)
        ctx.db.flush()
        ctx.response.delete_cookie(COOKIE, path="/", secure=config.production, httponly=True, samesite="lax")
        return {"ok": True}

    return app


def seed_demo(app):
    if app.state.config.production:
        raise RuntimeError("Demo seeding is disabled in production")
    passwords = [os.getenv("DEMO_STUDENT_PASSWORD", ""), os.getenv("DEMO_ADMIN_PASSWORD", "")]
    for password in passwords:
        try:
            check_password(password)
        except HTTPException as exc:
            raise RuntimeError("Set DEMO_STUDENT_PASSWORD and DEMO_ADMIN_PASSWORD: " + exc.detail) from exc
    with DBSession(app.state.engine) as db:
        lock_transaction(db)
        for email, name, role, password in zip(
            ["student@demo.investolingo.local", "admin@demo.investolingo.local"],
            ["Demo Student", "Demo Educator"], ["student", "educator_admin"], passwords,
        ):
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(id=uid(), email=email, name=name, role=role, birth_date="2000-01-01", created_at=now(),
                            password_hash=PASSWORDS.hash(password), email_verified=True)
                db.add(user)
                db.flush()
            else:
                user.password_hash = PASSWORDS.hash(password)
                user.email_verified = True
                user.role = role
                db.execute(delete(Session).where(Session.user_id == user.id))
                db.execute(delete(EmailToken).where(EmailToken.user_id == user.id))
            if db.get(World, user.id) is None:
                state = sim.new_state(secrets.randbits(53), today().isoformat())
                sim.run_day(state, offline=True, quiet=True)
                if sim.check_invariants(state):
                    raise RuntimeError("Demo simulation failed consistency checks")
                db.add(World(user_id=user.id, state=state))
        db.commit()
