"""Durable account, session, learning, classroom and simulation storage."""

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text)
    birth_date: Mapped[str] = mapped_column(String(10))
    role: Mapped[str] = mapped_column(String(20), default="student")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    plan: Mapped[str] = mapped_column(String(10), default="free")
    goal: Mapped[str] = mapped_column(String(300), default="")
    experience: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[int] = mapped_column(Integer)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class EmailToken(Base):
    __tablename__ = "email_tokens"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(10))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class World(Base):
    __tablename__ = "worlds"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON)


class WorldCheckpoint(Base):
    __tablename__ = "world_checkpoints"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer)


class LearningProfile(Base):
    __tablename__ = "learning_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    age_band: Mapped[str | None] = mapped_column(String(30), nullable=True)
    class_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    school: Mapped[str | None] = mapped_column(String(150), nullable=True)
    market: Mapped[str | None] = mapped_column(String(20), nullable=True)


class Ledger(Base):
    __tablename__ = "xp_ledger"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    award_key: Mapped[str] = mapped_column(String(200), unique=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(80))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[int] = mapped_column(Integer)


class Reflection(Base):
    __tablename__ = "reflections"
    __table_args__ = (UniqueConstraint("user_id", "day"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[str] = mapped_column(String(10))
    text: Mapped[str] = mapped_column(Text)


class Redemption(Base):
    __tablename__ = "redemptions"
    __table_args__ = (UniqueConstraint("user_id", "reward_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reward_id: Mapped[str] = mapped_column(String(50))
    cost: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[int] = mapped_column(Integer)


class Classroom(Base):
    __tablename__ = "classes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(16), unique=True)


class Membership(Base):
    __tablename__ = "memberships"
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (UniqueConstraint("class_id", "lesson_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(120))


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[int] = mapped_column(Integer, index=True)
