"""
定时轮询：每隔 N 分钟拉取所有用户的最新 Strava 活动
- 只拉取上次同步之后的新活动（增量同步）
- 新活动入库后自动计算 TSS + 异常检测
- 替代 Webhook，本地无需公网地址
"""

import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import User, Activity
from strava.sync import get_valid_token, fetch_activities_page, fetch_streams, parse_activity, parse_stream
from analysis.metrics import calc_tss_for_activity
from analysis.anomalies import detect_anomalies

logger = logging.getLogger(__name__)


async def poll_user(user: User, db: Session) -> dict:
    """
    增量同步单个用户的新活动。
    返回 {"new": N, "anomalies": [...]}
    """
    # 找到该用户最新活动的时间戳，作为增量起点
    latest = (
        db.query(Activity.start_date)
        .filter(Activity.user_id == user.id)
        .order_by(Activity.start_date.desc())
        .first()
    )
    if latest and latest[0]:
        # 从最新活动往前 1 小时开始拉，防止边界遗漏
        after_dt = latest[0].replace(tzinfo=timezone.utc) if latest[0].tzinfo is None else latest[0]
        after = int(after_dt.timestamp()) - 3600
    else:
        # 首次同步：从 2026 年 1 月 1 日起
        after = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())

    token = await get_valid_token(user, db)
    new_activities = []
    page = 1

    while True:
        raw_list = await fetch_activities_page(token, page, after)
        if not raw_list:
            break

        for raw in raw_list:
            strava_id = raw["id"]
            exists = db.query(Activity).filter(Activity.strava_id == strava_id).first()
            if exists:
                continue  # 已存在，跳过

            activity = parse_activity(raw, user.id)

            # 自动计算 TSS
            activity.tss = calc_tss_for_activity(activity, user)

            # 自动检测异常
            reasons = detect_anomalies(activity)
            if reasons:
                activity.is_excluded = True
                activity.exclude_reason = "；".join(reasons)
                activity.tss = None  # 异常数据不保留 TSS
                logger.warning(f"[轮询] 异常活动: {activity.name} | {reasons}")

            db.add(activity)
            db.flush()

            # 拉取 streams
            try:
                raw_streams = await fetch_streams(token, strava_id)
                if raw_streams:
                    stream = parse_stream(raw_streams, activity.id)
                    db.add(stream)
            except Exception as e:
                logger.warning(f"[轮询] stream 拉取失败: {strava_id} - {e}")

            db.commit()
            new_activities.append({
                "id": activity.id,
                "name": activity.name,
                "sport_type": activity.sport_type,
                "tss": activity.tss,
                "is_excluded": activity.is_excluded,
            })
            logger.info(f"[轮询] 新活动入库: {activity.name} ({activity.sport_type}) TSS={activity.tss}")

        page += 1

    return {"new": len(new_activities), "activities": new_activities}


async def poll_all_users():
    """
    轮询所有已授权用户（定时任务入口）。
    """
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            return

        logger.info(f"[轮询] 开始，共 {len(users)} 个用户")
        total_new = 0

        for user in users:
            try:
                result = await poll_user(user, db)
                total_new += result["new"]
                if result["new"] > 0:
                    logger.info(f"[轮询] 用户 {user.id}: 新增 {result['new']} 条活动")
            except Exception as e:
                logger.error(f"[轮询] 用户 {user.id} 失败: {e}")

        logger.info(f"[轮询] 完成，本次新增 {total_new} 条活动")
    finally:
        db.close()


def run_poll():
    """APScheduler 调用的同步入口（内部创建事件循环运行异步任务）"""
    asyncio.run(poll_all_users())
