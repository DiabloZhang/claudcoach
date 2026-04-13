from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from config import settings
from db.database import get_db
from db.models import User, SyncLog, Activity
from auth.dependencies import get_current_user, get_current_user_optional
from auth.security import create_access_token
from strava.client import get_authorization_url, exchange_code
from strava.sync import sync_user_activities

router = APIRouter(prefix="/strava", tags=["strava"])


@router.get("/login")
def login(state: str = None):
    """
    跳转到 Strava 授权页。
    ⚠️ 安全注意：state 参数目前复用传递 JWT 以识别当前用户（绑定模式）。
    JWT 会经过 Strava 服务器（出现在其日志中），存在泄露风险。
    TODO: 后续应改用随机 nonce + 服务端存储关联，避免 JWT 外泄。
    """
    return RedirectResponse(get_authorization_url(state=state))


@router.get("/callback")
async def callback(
    code: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Strava 授权回调，换取 token 并保存/更新用户。
    - 如果用户已登录（state 含 JWT），则绑定到当前账户
    - 否则尝试用 Strava 登录（已有账户则更新 token，否则创建新账户）
    """
    from auth.security import decode_access_token

    try:
        token_data = await exchange_code(code)
    except Exception:
        raise HTTPException(status_code=400, detail="Strava 授权失败，请重试")

    athlete = token_data.get("athlete", {})
    strava_id = athlete.get("id")
    if not strava_id:
        raise HTTPException(status_code=400, detail="无法获取用户信息")

    # 检查是否已登录（绑定模式）
    current_user = None
    if state:
        payload = decode_access_token(state)
        if payload and payload.get("sub"):
            current_user = db.query(User).filter(
                User.id == int(payload["sub"]), User.is_active
            ).first()

    if current_user:
        # 绑定到当前账户
        # 检查该 Strava 账户是否已被其他用户绑定
        existing_binding = db.query(User).filter(
            User.strava_athlete_id == strava_id,
            User.id != current_user.id,
        ).first()
        if existing_binding:
            return RedirectResponse(f"{settings.frontend_url}/settings?strava=error&detail=该Strava账户已被其他用户绑定")

        current_user.strava_athlete_id = strava_id
        current_user.access_token = token_data["access_token"]
        current_user.refresh_token = token_data["refresh_token"]
        current_user.token_expires_at = token_data["expires_at"]
        current_user.firstname = athlete.get("firstname") or current_user.firstname
        current_user.lastname = athlete.get("lastname") or current_user.lastname
        current_user.profile_pic = athlete.get("profile") or current_user.profile_pic
        if not current_user.email and athlete.get("email"):
            current_user.email = athlete.get("email")
        if current_user.auth_provider == "password":
            current_user.auth_provider = "both"
        db.commit()
        return RedirectResponse(f"{settings.frontend_url}/settings?strava=linked")

    # 查找或创建用户（登录模式）
    user = db.query(User).filter(User.strava_athlete_id == strava_id).first()
    if user:
        user.access_token = token_data["access_token"]
        user.refresh_token = token_data["refresh_token"]
        user.token_expires_at = token_data["expires_at"]
        user.firstname = athlete.get("firstname") or user.firstname
        user.lastname = athlete.get("lastname") or user.lastname
        user.profile_pic = athlete.get("profile") or user.profile_pic
        if not user.email and athlete.get("email"):
            user.email = athlete.get("email")
    else:
        user = User(
            strava_athlete_id=strava_id,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_expires_at=token_data["expires_at"],
            firstname=athlete.get("firstname"),
            lastname=athlete.get("lastname"),
            profile_pic=athlete.get("profile"),
            email=athlete.get("email"),
            nickname=athlete.get("firstname") or "Strava用户",
            auth_provider="strava",
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    # 生成 JWT 并跳回前端
    token = create_access_token({"sub": str(user.id)})
    return RedirectResponse(f"{settings.frontend_url}?auth=success&token={token}")


@router.get("/sync")
async def sync(
    background_tasks: BackgroundTasks,
    since: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    触发数据同步（后台执行）。
    since: 可选，格式 YYYY-MM-DD，从指定日期开始同步；不填则从最新活动时间起。
    """
    if not current_user.strava_athlete_id:
        raise HTTPException(status_code=400, detail="请先绑定 Strava 账户")
    since_dt = datetime.strptime(since, "%Y-%m-%d") if since else None
    background_tasks.add_task(sync_user_activities, current_user, db, since_dt)
    return {"message": "同步已开始", "since": since or "最新活动时间起"}


@router.get("/sync-logs")
def get_sync_logs(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取同步历史记录"""
    logs = (
        db.query(SyncLog)
        .filter(SyncLog.user_id == current_user.id)
        .order_by(SyncLog.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "started_at": log.started_at,
            "sync_from": log.sync_from,
            "activities_synced": log.activities_synced,
            "activities_skipped": log.activities_skipped,
            "strava_api_calls": log.strava_api_calls,
            "duration_seconds": log.duration_seconds,
            "status": log.status,
            "error_message": log.error_message,
        }
        for log in logs
    ]


@router.get("/activities")
def get_activities(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户活动列表"""
    activities = (
        db.query(Activity)
        .filter(Activity.user_id == current_user.id)
        .order_by(Activity.start_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": a.id,
            "strava_id": a.strava_id,
            "name": a.name,
            "sport_type": a.sport_type,
            "start_date": a.start_date,
            "distance": a.distance,
            "moving_time": a.moving_time,
            "avg_heart_rate": a.avg_heart_rate,
            "avg_power": a.avg_power,
            "tss": a.tss,
            "is_excluded": a.is_excluded,
            "exclude_reason": a.exclude_reason,
        }
        for a in activities
    ]


@router.get("/status")
def auth_status(
    current_user: User = Depends(get_current_user_optional),
):
    """检查当前用户认证状态"""
    if not current_user:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user_id": current_user.id,
        "name": f"{current_user.firstname or ''} {current_user.lastname or ''}".strip() or current_user.nickname,
        "profile_pic": current_user.profile_pic,
        "nickname": current_user.nickname,
        "email": current_user.email,
        "has_strava": bool(current_user.strava_athlete_id),
        "auth_provider": current_user.auth_provider,
    }
