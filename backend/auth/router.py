from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from db.database import get_db
from db.models import User, UserDataSource, UserState
from auth.security import verify_password, get_password_hash, create_access_token, encrypt_token
from auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    timezone: Optional[str] = None
    sleep_time: Optional[str] = None
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    old_password: Optional[str] = None
    new_password: str


class DataSourceRequest(BaseModel):
    provider: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


# ── 注册 ─────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")

    user = User(
        email=body.email,
        password_hash=get_password_hash(body.password),
        nickname=body.nickname or body.email.split("@")[0],
        auth_provider="password",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _user_to_dict(user),
    }


# ── 登录 ─────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")

    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _user_to_dict(user),
    }


# ── 当前用户信息 ─────────────────────────────────────────

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return _user_to_dict(current_user)


# ── 修改资料 ─────────────────────────────────────────────

@router.put("/profile")
def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.nickname is not None:
        current_user.nickname = body.nickname
    if body.timezone is not None:
        current_user.timezone = body.timezone
    if body.sleep_time is not None:
        current_user.sleep_time = body.sleep_time
    if body.email is not None:
        if body.email != current_user.email:
            existing = db.query(User).filter(User.email == body.email).first()
            if existing:
                raise HTTPException(status_code=400, detail="该邮箱已被其他账户使用")
            current_user.email = body.email
    db.commit()
    return {"ok": True, "user": _user_to_dict(current_user)}


# ── 修改密码 ─────────────────────────────────────────────

@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.password_hash:
        # 已设置密码：必须提供正确的原密码
        if not body.old_password or not verify_password(body.old_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="原密码错误")
    else:
        # 未设置密码：不应提供原密码
        if body.old_password:
            raise HTTPException(status_code=400, detail="当前账户未设置原密码，请勿填写原密码")
    current_user.password_hash = get_password_hash(body.new_password)
    db.commit()
    return {"ok": True}


# ── Strava OAuth ─────────────────────────────────────────

@router.post("/strava/disconnect")
def strava_disconnect(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """解除 Strava 绑定。若当前账户未设置密码，则禁止解绑，避免用户被锁在外面。"""
    if not current_user.password_hash:
        raise HTTPException(
            status_code=400,
            detail="请先设置密码后再解除 Strava 绑定，否则将无法登录",
        )

    current_user.strava_athlete_id = None
    current_user.access_token = None
    current_user.refresh_token = None
    current_user.token_expires_at = None
    if current_user.auth_provider in ("both", "strava"):
        current_user.auth_provider = "password"
    db.commit()
    return {"ok": True}


# ── 数据源管理 ───────────────────────────────────────────

@router.get("/data-sources")
def list_data_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sources = db.query(UserDataSource).filter(UserDataSource.user_id == current_user.id).all()
    return [
        {
            "id": s.id,
            "provider": s.provider,
            "client_id": s.client_id,
            "athlete_id": s.athlete_id,
            "has_token": bool(s.access_token_encrypted),
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in sources
    ]


@router.post("/data-sources")
def create_data_source(
    body: DataSourceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(UserDataSource).filter(
        UserDataSource.user_id == current_user.id,
        UserDataSource.provider == body.provider,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"已存在 {body.provider} 数据源")

    source = UserDataSource(
        user_id=current_user.id,
        provider=body.provider,
        client_id=body.client_id,
        client_secret_encrypted=encrypt_token(body.client_secret) if body.client_secret else None,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return {"id": source.id, "provider": source.provider}


@router.delete("/data-sources/{source_id}")
def delete_data_source(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    source = db.query(UserDataSource).filter(
        UserDataSource.id == source_id,
        UserDataSource.user_id == current_user.id,
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    db.delete(source)
    db.commit()
    return {"ok": True}


# ── 用户状态管理（LLM 上下文等大文本）──────────────────────

@router.get("/state/{key}")
def get_state(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    state = db.query(UserState).filter(
        UserState.user_id == current_user.id,
        UserState.state_key == key,
    ).first()
    if not state:
        return {"key": key, "value": None}
    return {"key": key, "value": state.state_value, "updated_at": state.updated_at}


@router.post("/state/{key}")
def set_state(
    key: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    state = db.query(UserState).filter(
        UserState.user_id == current_user.id,
        UserState.state_key == key,
    ).first()
    value = body.get("value", "")
    if state:
        state.state_value = value
    else:
        state = UserState(user_id=current_user.id, state_key=key, state_value=value)
        db.add(state)
    db.commit()
    return {"ok": True}


@router.delete("/state/{key}")
def delete_state(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    state = db.query(UserState).filter(
        UserState.user_id == current_user.id,
        UserState.state_key == key,
    ).first()
    if state:
        db.delete(state)
        db.commit()
    return {"ok": True}


# ── Helpers ──────────────────────────────────────────────

def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "profile_pic": user.profile_pic,
        "auth_provider": user.auth_provider,
        "has_strava": bool(user.strava_athlete_id),
        "has_password": bool(user.password_hash),
        "timezone": user.timezone,
        "sleep_time": user.sleep_time,
        "ftp": user.ftp,
        "lthr": user.lthr,
        "css": user.css,
        "run_threshold_pace": user.run_threshold_pace,
    }
