import httpx
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import User, Activity, Stream, SyncLog
from strava.client import STRAVA_API_BASE, refresh_access_token, is_token_expired
from analysis.anomalies import detect_anomalies

STREAM_KEYS = "time,heartrate,watts,velocity_smooth,cadence,altitude,distance"
SYNC_DAYS = 30  # 只同步最近 N 天


async def get_valid_token(user: User, db: Session) -> str:
    """获取有效 token，过期则自动刷新"""
    if is_token_expired(user.token_expires_at):
        data = await refresh_access_token(user.refresh_token)
        user.access_token = data["access_token"]
        user.refresh_token = data["refresh_token"]
        user.token_expires_at = data["expires_at"]
        db.commit()
    return user.access_token


async def fetch_activities_page(token: str, page: int, after: int, per_page: int = 50) -> list:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{STRAVA_API_BASE}/athlete/activities",
            headers={"Authorization": f"Bearer {token}"},
            params={"page": page, "per_page": per_page, "after": after},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_streams(token: str, activity_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{STRAVA_API_BASE}/activities/{activity_id}/streams",
            headers={"Authorization": f"Bearer {token}"},
            params={"keys": STREAM_KEYS, "key_by_type": "true"},
            timeout=30,
        )
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        return resp.json()


def parse_activity(raw: dict, user_id: int) -> Activity:
    """将 Strava 原始 activity 数据转为数据库模型"""
    start_date = None
    if raw.get("start_date"):
        start_date = datetime.strptime(raw["start_date"], "%Y-%m-%dT%H:%M:%SZ")

    start_date_local = None
    if raw.get("start_date_local"):
        start_date_local = datetime.strptime(raw["start_date_local"], "%Y-%m-%dT%H:%M:%SZ")

    # 配速：秒/km（从 m/s 换算）
    avg_speed = raw.get("average_speed", 0)
    avg_pace = (1000 / avg_speed) if avg_speed > 0 else None

    return Activity(
        user_id=user_id,
        strava_id=raw["id"],
        name=raw.get("name"),
        sport_type=raw.get("sport_type") or raw.get("type"),
        start_date=start_date,
        start_date_local=start_date_local,
        timezone=raw.get("timezone"),
        distance=raw.get("distance"),
        moving_time=raw.get("moving_time"),
        elapsed_time=raw.get("elapsed_time"),
        elevation_gain=raw.get("total_elevation_gain"),
        avg_heart_rate=raw.get("average_heartrate"),
        max_heart_rate=raw.get("max_heartrate"),
        avg_power=raw.get("average_watts"),
        normalized_power=raw.get("weighted_average_watts"),
        max_power=raw.get("max_watts"),
        avg_cadence=raw.get("average_cadence"),
        avg_pace=avg_pace,
        avg_stroke_rate=raw.get("average_stroke_rate"),
        pool_length=raw.get("pool_length"),
    )


def parse_stream(raw: dict, activity_id: int) -> Stream:
    def get_data(key):
        return raw[key]["data"] if key in raw else None

    return Stream(
        activity_id=activity_id,
        time=get_data("time"),
        heart_rate=get_data("heartrate"),
        watts=get_data("watts"),
        velocity_smooth=get_data("velocity_smooth"),
        cadence=get_data("cadence"),
        altitude=get_data("altitude"),
        distance=get_data("distance"),
    )


async def sync_user_activities(user: User, db: Session, since: datetime = None) -> dict:
    """
    同步用户活动。since 指定从哪个时间点开始，默认从最新活动时间起。
    返回同步统计（含 Strava API 调用次数）。
    """
    started_at = datetime.utcnow()
    t0 = time.time()
    token = await get_valid_token(user, db)
    api_calls = 0

    # 确定同步起点
    if since is None:
        latest = db.query(Activity).filter(
            Activity.user_id == user.id
        ).order_by(Activity.start_date.desc()).first()
        since = latest.start_date if latest else datetime(2026, 1, 1)

    after = int(since.timestamp())
    sync_from = since

    synced = 0
    skipped = 0
    page = 1

    try:
        while True:
            raw_activities = await fetch_activities_page(token, page, after)
            api_calls += 1
            if not raw_activities:
                break

            for raw in raw_activities:
                strava_id = raw["id"]

                exists = db.query(Activity).filter(
                    Activity.strava_id == strava_id
                ).first()
                if exists:
                    skipped += 1
                    continue

                activity = parse_activity(raw, user.id)

                reasons = detect_anomalies(activity)
                if reasons:
                    activity.is_excluded = True
                    activity.exclude_reason = "；".join(reasons)
                    activity.tss_adjusted = 0.0

                db.add(activity)
                db.flush()

                try:
                    raw_streams = await fetch_streams(token, strava_id)
                    api_calls += 1
                    if raw_streams:
                        stream = parse_stream(raw_streams, activity.id)
                        db.add(stream)
                except Exception:
                    pass

                db.commit()
                synced += 1

            page += 1

        status = "success"
        error_message = None
    except Exception as e:
        status = "error"
        error_message = str(e)

    duration = time.time() - t0

    log = SyncLog(
        user_id=user.id,
        started_at=started_at,
        sync_from=sync_from,
        activities_synced=synced,
        activities_skipped=skipped,
        strava_api_calls=api_calls,
        duration_seconds=round(duration, 1),
        status=status,
        error_message=error_message,
    )
    db.add(log)
    db.commit()

    return {"synced": synced, "skipped": skipped, "api_calls": api_calls, "duration": round(duration, 1)}
