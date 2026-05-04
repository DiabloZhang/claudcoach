from typing import Any
from sqlalchemy import (
    Integer, BigInteger, String, Float, DateTime, Text, ForeignKey, JSON, Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # 账户登录信息
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    nickname: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    auth_provider: Mapped[str] = mapped_column(String, default="password")

    # Strava OAuth 信息
    strava_athlete_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    access_token: Mapped[str | None] = mapped_column(String, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    token_expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 个人信息
    firstname: Mapped[str | None] = mapped_column(String)
    lastname: Mapped[str | None] = mapped_column(String)
    profile_pic: Mapped[str | None] = mapped_column(String)

    # 训练阈值
    ftp: Mapped[float | None] = mapped_column(Float)
    lthr: Mapped[float | None] = mapped_column(Float)
    css: Mapped[float | None] = mapped_column(Float)
    run_threshold_pace: Mapped[float | None] = mapped_column(Float)

    # AI 教练相关
    timezone: Mapped[str] = mapped_column(String, default="Asia/Shanghai")
    sleep_time: Mapped[str] = mapped_column(String, default="22:00")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    activities: Mapped[list["Activity"]] = relationship(
        "Activity", back_populates="user"
    )
    data_sources: Mapped[list["UserDataSource"]] = relationship(
        "UserDataSource", back_populates="user", cascade="all, delete-orphan"
    )
    states: Mapped[list["UserState"]] = relationship(
        "UserState", back_populates="user", cascade="all, delete-orphan"
    )


class UserDataSource(Base):
    """用户上游数据源认证信息"""
    __tablename__ = "user_data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)

    client_id: Mapped[str | None] = mapped_column(String, nullable=True)
    client_secret_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)

    access_token_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    token_expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    athlete_id: Mapped[str | None] = mapped_column(String, nullable=True)

    settings: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="data_sources")


class UserState(Base):
    """用户状态信息"""
    __tablename__ = "user_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    state_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    state_value: Mapped[str] = mapped_column(Text, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="states")


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("user_id", "strava_id", name="uix_activity_user_strava"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    strava_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    name: Mapped[str | None] = mapped_column(String)
    sport_type: Mapped[str | None] = mapped_column(String)
    start_date: Mapped[datetime | None] = mapped_column(DateTime)
    start_date_local: Mapped[datetime | None] = mapped_column(DateTime)
    timezone: Mapped[str | None] = mapped_column(String)

    distance: Mapped[float | None] = mapped_column(Float)
    moving_time: Mapped[int | None] = mapped_column(Integer)
    elapsed_time: Mapped[int | None] = mapped_column(Integer)
    elevation_gain: Mapped[float | None] = mapped_column(Float)

    avg_heart_rate: Mapped[float | None] = mapped_column(Float)
    max_heart_rate: Mapped[float | None] = mapped_column(Float)

    avg_power: Mapped[float | None] = mapped_column(Float)
    normalized_power: Mapped[float | None] = mapped_column(Float)
    max_power: Mapped[float | None] = mapped_column(Float)

    avg_cadence: Mapped[float | None] = mapped_column(Float)
    avg_pace: Mapped[float | None] = mapped_column(Float)

    avg_stroke_rate: Mapped[float | None] = mapped_column(Float)
    pool_length: Mapped[float | None] = mapped_column(Float)

    tss: Mapped[float | None] = mapped_column(Float)
    intensity_factor: Mapped[float | None] = mapped_column(Float)

    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    exclude_reason: Mapped[str | None] = mapped_column(String)
    tss_adjusted: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="activities")
    streams: Mapped[list["Stream"]] = relationship(
        "Stream", back_populates="activity", cascade="all, delete-orphan"
    )


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_from: Mapped[datetime | None] = mapped_column(DateTime)
    activities_synced: Mapped[int] = mapped_column(Integer, default=0)
    activities_skipped: Mapped[int] = mapped_column(Integer, default=0)
    strava_api_calls: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="success")
    error_message: Mapped[str | None] = mapped_column(String)


class CoachPersona(Base):
    __tablename__ = "coach_personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, default="Coach Alex")
    personality: Mapped[str] = mapped_column(
        Text, default="专业、直接但温暖的铁三教练，有15年执教经验"
    )
    style: Mapped[str] = mapped_column(String, default="专业但不冷漠，会用具体数据支撑建议")
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    activity_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("activities.id"), nullable=True
    )
    trigger: Mapped[str] = mapped_column(String, default="activity_review")
    status: Mapped[str] = mapped_column(String, default="pending")
    training_type: Mapped[str | None] = mapped_column(String)
    rpe: Mapped[int | None] = mapped_column(Integer)
    body_status: Mapped[str | None] = mapped_column(String)
    life_stress: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )


class Stream(Base):
    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("activities.id"), nullable=False
    )

    time: Mapped[list[Any] | None] = mapped_column(JSON)
    heart_rate: Mapped[list[Any] | None] = mapped_column(JSON)
    watts: Mapped[list[Any] | None] = mapped_column(JSON)
    velocity_smooth: Mapped[list[Any] | None] = mapped_column(JSON)
    cadence: Mapped[list[Any] | None] = mapped_column(JSON)
    altitude: Mapped[list[Any] | None] = mapped_column(JSON)
    distance: Mapped[list[Any] | None] = mapped_column(JSON)

    activity: Mapped["Activity"] = relationship("Activity", back_populates="streams")
