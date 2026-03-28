from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import User
from strava.client import get_authorization_url, exchange_code, get_athlete
from strava.sync import sync_user_activities
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
def login():
    """跳转到 Strava 授权页"""
    return RedirectResponse(get_authorization_url())


@router.get("/callback")
async def callback(code: str, db: Session = Depends(get_db)):
    """Strava 授权回调，换取 token 并保存用户"""
    try:
        token_data = await exchange_code(code)
    except Exception:
        raise HTTPException(status_code=400, detail="Strava 授权失败，请重试")

    athlete = token_data.get("athlete", {})
    strava_id = athlete.get("id")

    if not strava_id:
        raise HTTPException(status_code=400, detail="无法获取用户信息")

    # 已存在则更新 token，否则新建
    user = db.query(User).filter(User.strava_athlete_id == strava_id).first()
    if user:
        user.access_token = token_data["access_token"]
        user.refresh_token = token_data["refresh_token"]
        user.token_expires_at = token_data["expires_at"]
    else:
        user = User(
            strava_athlete_id=strava_id,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_expires_at=token_data["expires_at"],
            firstname=athlete.get("firstname"),
            lastname=athlete.get("lastname"),
            profile_pic=athlete.get("profile"),
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    # 授权完成，跳回前端
    return RedirectResponse(f"{settings.frontend_url}?auth=success&user_id={user.id}")


@router.get("/sync/{user_id}")
async def sync(user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """触发历史数据同步（后台执行，不阻塞请求）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    background_tasks.add_task(sync_user_activities, user, db)
    return {"message": "同步已开始，请稍后查看活动列表"}


@router.get("/activities/{user_id}")
def get_activities(user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """获取用户活动列表"""
    from db.models import Activity
    activities = (
        db.query(Activity)
        .filter(Activity.user_id == user_id)
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
def auth_status(user_id: int, db: Session = Depends(get_db)):
    """检查用户是否已授权"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user_id": user.id,
        "name": f"{user.firstname} {user.lastname}",
        "profile_pic": user.profile_pic,
    }
