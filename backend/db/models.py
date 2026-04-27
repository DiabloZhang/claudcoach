from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Text, ForeignKey, JSON, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    # 账户登录信息
    email = Column(String, unique=True, nullable=True, index=True)
    password_hash = Column(String, nullable=True)
    nickname = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    auth_provider = Column(String, default="password")  # password | strava | both

    # Strava OAuth 信息（保留在 User 表保证向后兼容，也作为主要数据源）
    strava_athlete_id = Column(Integer, unique=True, nullable=True)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    token_expires_at = Column(Integer, nullable=True)  # unix timestamp

    # 个人信息
    firstname = Column(String)
    lastname = Column(String)
    profile_pic = Column(String)

    # 训练阈值（用于指标计算）
    ftp = Column(Float)        # 功能阈值功率（骑行，瓦特）
    lthr = Column(Float)       # 乳酸阈值心率（骑行/跑步，bpm）
    css = Column(Float)        # 临界游泳速度（游泳，秒/100m）
    run_threshold_pace = Column(Float)  # 跑步阈值配速（秒/km）

    # AI 教练相关
    timezone = Column(String, default="Asia/Shanghai")
    sleep_time = Column(String, default="22:00")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    activities = relationship("Activity", back_populates="user")
    data_sources = relationship("UserDataSource", back_populates="user", cascade="all, delete-orphan")
    states = relationship("UserState", back_populates="user", cascade="all, delete-orphan")
    injuries = relationship("UserInjury", back_populates="user", cascade="all, delete-orphan")


class UserDataSource(Base):
    """用户上游数据源认证信息（支持多数据源）"""
    __tablename__ = "user_data_sources"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String, nullable=False)  # strava, garmin, etc.

    # 应用级凭证（用户可配置自己的 Strava App）
    client_id = Column(String, nullable=True)
    client_secret_encrypted = Column(String, nullable=True)  # Fernet 加密

    # 用户级凭证
    access_token_encrypted = Column(String, nullable=True)   # Fernet 加密
    refresh_token_encrypted = Column(String, nullable=True)  # Fernet 加密
    token_expires_at = Column(Integer, nullable=True)        # unix timestamp
    athlete_id = Column(String, nullable=True)

    # 额外配置
    settings = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="data_sources")


class UserState(Base):
    """用户状态信息（LLM 上下文、教练记忆等大文本）"""
    __tablename__ = "user_states"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    state_key = Column(String, nullable=False, index=True)   # 如 llm_context, coach_memory
    state_value = Column(Text, nullable=False)               # 大文本 / JSON 字符串

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="states")


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("user_id", "strava_id", name="uix_activity_user_strava"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strava_id = Column(BigInteger, nullable=False)

    # 基础信息
    name = Column(String)
    sport_type = Column(String)   # Swim / Ride / Run / VirtualRide 等
    start_date = Column(DateTime)        # UTC
    start_date_local = Column(DateTime)  # 用户当地时间（展示用）
    timezone = Column(String)

    # 运动数据
    distance = Column(Float)        # 米
    moving_time = Column(Integer)   # 秒
    elapsed_time = Column(Integer)  # 秒
    elevation_gain = Column(Float)  # 米

    # 心率
    avg_heart_rate = Column(Float)
    max_heart_rate = Column(Float)

    # 骑行功率
    avg_power = Column(Float)
    normalized_power = Column(Float)
    max_power = Column(Float)

    # 跑步
    avg_cadence = Column(Float)     # 步频
    avg_pace = Column(Float)        # 秒/km

    # 游泳
    avg_stroke_rate = Column(Float)
    pool_length = Column(Float)

    # 计算指标
    tss = Column(Float)             # 训练压力分
    intensity_factor = Column(Float)

    # 数据质量
    is_excluded = Column(Boolean, default=False)   # True = 脏数据，排除出计算
    exclude_reason = Column(String)                # 排除原因（自动检测 or 手动）
    tss_adjusted = Column(Float, default=0.0)      # 异常数据的修正 TSS（默认0，未来可人工修正为估算值）

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="activities")
    streams = relationship("Stream", back_populates="activity", cascade="all, delete-orphan")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    sync_from = Column(DateTime)          # 从哪个时间点开始同步
    activities_synced = Column(Integer, default=0)
    activities_skipped = Column(Integer, default=0)
    strava_api_calls = Column(Integer, default=0)
    duration_seconds = Column(Float)
    status = Column(String, default="success")   # success / error
    error_message = Column(String)


class CoachPersona(Base):
    __tablename__ = "coach_personas"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, default="Coach Alex")
    personality = Column(Text, default="专业、直接但温暖的铁三教练，有15年执教经验")
    style = Column(String, default="专业但不冷漠，会用具体数据支撑建议")
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True)  # 关联的训练（可选）
    trigger = Column(String, default="activity_review")  # activity_review / weekly / alert / chat
    status = Column(String, default="pending")  # pending / active / complete
    # 提取的结构化数据
    training_type = Column(String)   # interval / tempo / aerobic / recovery / long
    rpe = Column(Integer)            # 1-10
    body_status = Column(String)     # normal / fatigue / pain / sick
    life_stress = Column(String)     # none / mild / significant
    notes = Column(Text)             # 对话摘要
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation", order_by="Message.id")
    topics = relationship("ConversationTopic", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)   # "coach" / "user"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class ConversationTopic(Base):
    __tablename__ = "conversation_topics"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    topic = Column(String, nullable=False, index=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="topics")


class UserInjury(Base):
    __tablename__ = "user_injuries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, default="active", index=True)  # active / recovering / resolved
    body_part = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="injuries")
    conversation_refs = relationship("InjuryConversationRef", back_populates="injury", cascade="all, delete-orphan")


class InjuryConversationRef(Base):
    __tablename__ = "injury_conversation_refs"

    id = Column(Integer, primary_key=True)
    injury_id = Column(Integer, ForeignKey("user_injuries.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    ref_type = Column(String, default="followup")  # first_mention / followup / resolution
    created_at = Column(DateTime, default=datetime.utcnow)

    injury = relationship("UserInjury", back_populates="conversation_refs")
    conversation = relationship("Conversation")


class ModelCallLog(Base):
    __tablename__ = "model_call_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    task = Column(String, nullable=False)
    model = Column(String, nullable=True)
    request_json = Column(JSON, nullable=True)
    response_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    conversation = relationship("Conversation")


class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)

    # 原始时序数据，存为 JSON 数组（每秒一个点）
    time = Column(JSON)           # 时间戳列表
    heart_rate = Column(JSON)     # 心率流
    watts = Column(JSON)          # 功率流
    velocity_smooth = Column(JSON)  # 速度流（m/s）
    cadence = Column(JSON)        # 踏频/步频流
    altitude = Column(JSON)       # 海拔流
    distance = Column(JSON)       # 距离流

    activity = relationship("Activity", back_populates="streams")
