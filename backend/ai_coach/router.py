from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import User, Activity, Conversation, Message, CoachPersona
from ai_coach.coach import (
    get_or_create_persona, build_first_message, chat, extract_structured_data
)
from datetime import date
import math

router = APIRouter(prefix="/coach", tags=["coach"])


def _get_fitness_values(user_id: int, db: Session):
    """计算当前 CTL/ATL/TSB"""
    try:
        activities = db.query(Activity).filter_by(user_id=user_id).all()
        daily_tss: dict[date, float] = {}
        for a in activities:
            if not a.start_date:
                continue
            effective = a.tss_adjusted if a.is_excluded else a.tss
            if effective is None:
                continue
            d = a.start_date.date() if hasattr(a.start_date, "date") else a.start_date
            daily_tss[d] = daily_tss.get(d, 0.0) + effective

        if not daily_tss:
            return None, None, None

        start = min(daily_tss.keys())
        end = date.today()
        ctl = atl = 0.0
        k_ctl = 2 / (42 + 1)
        k_atl = 2 / (7 + 1)
        cur = start
        while cur <= end:
            tss = daily_tss.get(cur, 0.0)
            ctl = tss * k_ctl + ctl * (1 - k_ctl)
            atl = tss * k_atl + atl * (1 - k_atl)
            cur = date.fromordinal(cur.toordinal() + 1)
        tsb = ctl - atl
        return round(ctl, 1), round(atl, 1), round(tsb, 1)
    except Exception:
        return None, None, None


# ── 教练人设 ──────────────────────────────────────────────

@router.get("/persona/{user_id}")
def get_persona(user_id: int, db: Session = Depends(get_db)):
    persona = get_or_create_persona(user_id, db)
    return {
        "name": persona.name,
        "personality": persona.personality,
        "style": persona.style,
    }


class PersonaUpdate(BaseModel):
    name: str = None
    personality: str = None
    style: str = None


@router.put("/persona/{user_id}")
def update_persona(user_id: int, body: PersonaUpdate, db: Session = Depends(get_db)):
    persona = get_or_create_persona(user_id, db)
    if body.name is not None:
        persona.name = body.name
    if body.personality is not None:
        persona.personality = body.personality
    if body.style is not None:
        persona.style = body.style
    db.commit()
    return {"ok": True}


# ── 对话列表 ──────────────────────────────────────────────

@router.get("/conversations/{user_id}")
def list_conversations(user_id: int, db: Session = Depends(get_db)):
    convs = (db.query(Conversation)
             .filter_by(user_id=user_id)
             .order_by(Conversation.created_at.desc())
             .limit(20).all())
    return [
        {
            "id": c.id,
            "trigger": c.trigger,
            "status": c.status,
            "notes": c.notes,
            "created_at": c.created_at,
        }
        for c in convs
    ]


# ── 打开 Coach 页面：返回待处理对话（或新建空对话）──────────

@router.get("/open/{user_id}")
def open_coach(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    persona = get_or_create_persona(user_id, db)
    ctl, atl, tsb = _get_fitness_values(user_id, db)

    # 找最老的 pending 对话
    conv = (db.query(Conversation)
            .filter_by(user_id=user_id, status="pending")
            .order_by(Conversation.created_at.asc())
            .first())

    if not conv:
        # 没有 pending，创建一个闲聊对话
        conv = Conversation(user_id=user_id, trigger="chat", status="active")
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 如果还没有任何消息，生成教练开场白
    if not conv.messages:
        activity = None
        if conv.activity_id:
            activity = db.query(Activity).filter_by(id=conv.activity_id).first()

        try:
            first_msg = build_first_message(user, persona, db, activity, ctl, atl, tsb)
        except Exception as e:
            first_msg = f"你好，{user.firstname or '运动员'}！我是你的教练 {persona.name}，跟我聊聊最近的训练吧。"
            import logging
            logging.error(f"Coach first message failed: {e}")

        msg = Message(conversation_id=conv.id, role="coach", content=first_msg)
        db.add(msg)
        conv.status = "active"
        db.commit()
        db.refresh(conv)

    return {
        "conversation_id": conv.id,
        "trigger": conv.trigger,
        "status": conv.status,
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at}
            for m in conv.messages
        ],
    }


# ── 发送消息 ──────────────────────────────────────────────

class ChatInput(BaseModel):
    content: str


@router.post("/message/{conversation_id}")
def send_message(conversation_id: int, body: ChatInput, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    if conv.status == "complete":
        raise HTTPException(400, "Conversation already complete")

    user = db.query(User).filter_by(id=conv.user_id).first()
    persona = get_or_create_persona(conv.user_id, db)
    ctl, atl, tsb = _get_fitness_values(conv.user_id, db)

    # 存用户消息
    db.add(Message(conversation_id=conv.id, role="user", content=body.content))
    db.commit()

    # 调用 Claude
    try:
        reply, is_done = chat(conv, body.content, user, persona, db, ctl, atl, tsb)
    except Exception as e:
        import logging
        logging.error(f"Coach chat failed: {e}")
        raise HTTPException(500, f"教练暂时无法回复：{str(e)}")

    # 存教练回复
    db.add(Message(conversation_id=conv.id, role="coach", content=reply))

    if is_done:
        conv.status = "complete"
        # 异步提取结构化数据
        db.commit()
        db.refresh(conv)
        try:
            data = extract_structured_data(conv)
            conv.training_type = data.get("training_type")
            conv.rpe = data.get("rpe")
            conv.body_status = data.get("body_status")
            conv.life_stress = data.get("life_stress")
            conv.notes = data.get("notes")
        except Exception:
            pass

    db.commit()

    return {
        "reply": reply,
        "is_complete": is_done,
    }


# ── 活动同步后创建待处理对话（供 sync 调用）──────────────────

def create_pending_conversation(user_id: int, activity_id: int, db: Session):
    conv = Conversation(
        user_id=user_id,
        activity_id=activity_id,
        trigger="activity_review",
        status="pending",
    )
    db.add(conv)
    db.commit()
