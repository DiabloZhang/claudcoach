from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    strava_athlete_id = Column(Integer, unique=True, nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    token_expires_at = Column(Integer, nullable=False)  # unix timestamp

    # 个人信息
    firstname = Column(String)
    lastname = Column(String)
    profile_pic = Column(String)

    # 训练阈值（用于指标计算）
    ftp = Column(Float)        # 功能阈值功率（骑行，瓦特）
    lthr = Column(Float)       # 乳酸阈值心率（骑行/跑步，bpm）
    css = Column(Float)        # 临界游泳速度（游泳，秒/100m）
    run_threshold_pace = Column(Float)  # 跑步阈值配速（秒/km）

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    activities = relationship("Activity", back_populates="user")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strava_id = Column(BigInteger, unique=True, nullable=False)

    # 基础信息
    name = Column(String)
    sport_type = Column(String)   # Swim / Ride / Run / VirtualRide 等
    start_date = Column(DateTime)
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
