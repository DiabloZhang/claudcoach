from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import User, Activity, Conversation, ConversationTopic, Message, ModelCallLog, UserInjury, UserState
from auth.dependencies import get_current_user
from ai_coach.coach import (
    get_or_create_persona, build_first_message, chat, extract_structured_data,
    detect_persona_name, find_avatar_url,
)
from ai_coach.llm import LLMTask, MODELS
from ai_coach.topics import process_conversation_topics
from config import settings
from datetime import date
import threading
import traceback

router = APIRouter(prefix="/coach", tags=["coach"])

MODEL_PROVIDER_ORDER_KEY = "coach_model_provider_order"
DEFAULT_PROVIDER_ORDER = ["gemini", "anthropic"]
TOPIC_DETECT_USER_MESSAGE_INTERVAL = 3
TOPIC_DETECT_DELAY_SECONDS = 600
TOPIC_SUMMARY_USER_MESSAGE_WINDOW = 20


def _get_provider_order(user_id: int, db: Session) -> list[str]:
    state = db.query(UserState).filter_by(
        user_id=user_id,
        state_key=MODEL_PROVIDER_ORDER_KEY,
    ).first()
    if not state:
        return DEFAULT_PROVIDER_ORDER
    try:
        import json
        order = json.loads(state.state_value)
    except Exception:
        return DEFAULT_PROVIDER_ORDER
    order = [p for p in order if p in ("gemini", "anthropic")]
    for provider in DEFAULT_PROVIDER_ORDER:
        if provider not in order:
            order.append(provider)
    return order


def _set_provider_order(user_id: int, db: Session, order: list[str]) -> list[str]:
    import json

    clean = [p for p in order if p in ("gemini", "anthropic")]
    if not clean:
        clean = DEFAULT_PROVIDER_ORDER
    for provider in DEFAULT_PROVIDER_ORDER:
        if provider not in clean:
            clean.append(provider)

    state = db.query(UserState).filter_by(
        user_id=user_id,
        state_key=MODEL_PROVIDER_ORDER_KEY,
    ).first()
    if not state:
        state = UserState(user_id=user_id, state_key=MODEL_PROVIDER_ORDER_KEY, state_value="[]")
        db.add(state)
    state.state_value = json.dumps(clean, ensure_ascii=False)
    db.commit()
    return clean


def _user_message_count(conv: Conversation) -> int:
    return sum(1 for msg in conv.messages if msg.role == "user")


def _conversation_topic_names(conversation_id: int, db: Session) -> list[str]:
    rows = (
        db.query(ConversationTopic)
        .filter_by(conversation_id=conversation_id)
        .order_by(ConversationTopic.created_at.desc())
        .all()
    )
    seen = set()
    names = []
    for row in rows:
        if row.topic in seen:
            continue
        seen.add(row.topic)
        names.append(row.topic)
    return names


@router.get("/debug")
def debug_llm():
    """诊断 LLM 配置和连通性"""
    result = {
        "llm_provider": settings.llm_provider,
        "gemini_api_key_set": bool(settings.gemini_api_key),
        "anthropic_api_key_set": bool(settings.anthropic_api_key),
        "gemini_test": None,
        "gemini_error": None,
    }
    try:
        from google import genai
        from google.genai import types as genai_types
        client = genai.Client(api_key=settings.gemini_api_key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[genai_types.Content(role="user", parts=[genai_types.Part(text="say hi")])],
            config=genai_types.GenerateContentConfig(max_output_tokens=20),
        )
        result["gemini_test"] = resp.text
    except Exception as e:
        result["gemini_error"] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
    return result


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

@router.get("/persona")
def get_persona(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    persona = get_or_create_persona(current_user.id, db)
    return {
        "name": persona.name,
        "personality": persona.personality,
        "style": persona.style,
    }


class PersonaUpdate(BaseModel):
    name: str = None
    personality: str = None
    style: str = None


@router.put("/persona")
def update_persona(body: PersonaUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    persona = get_or_create_persona(current_user.id, db)
    if body.name is not None:
        persona.name = body.name
    if body.personality is not None:
        persona.personality = body.personality
    if body.style is not None:
        persona.style = body.style
    db.commit()
    return {"ok": True}


class ModelPreferenceUpdate(BaseModel):
    provider_order: list[str]


@router.get("/model-preference")
def get_model_preference(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {
        "provider_order": _get_provider_order(current_user.id, db),
        "available_providers": DEFAULT_PROVIDER_ORDER,
    }


@router.put("/model-preference")
def update_model_preference(
    body: ModelPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"provider_order": _set_provider_order(current_user.id, db, body.provider_order)}


# ── 对话列表 ──────────────────────────────────────────────

@router.get("/conversations")
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = (db.query(Conversation)
             .filter_by(user_id=current_user.id)
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


@router.get("/notes")
def get_coach_notes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    injuries = (
        db.query(UserInjury)
        .filter_by(user_id=current_user.id)
        .order_by(UserInjury.updated_at.desc())
        .all()
    )
    return {
        "injuries": [
            {
                "id": i.id,
                "status": i.status,
                "body_part": i.body_part,
                "summary": i.summary,
                "notes": i.notes,
                "created_at": i.created_at,
                "updated_at": i.updated_at,
            }
            for i in injuries
        ]
    }


# ── 打开 Coach 页面：返回待处理对话（或新建空对话）──────────

@router.get("/open")
def open_coach(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    persona = get_or_create_persona(current_user.id, db)
    ctl, atl, tsb = _get_fitness_values(current_user.id, db)
    provider_order = _get_provider_order(current_user.id, db)
    model_used = None

    # 优先找最老的 pending 对话
    conv = (db.query(Conversation)
            .filter_by(user_id=current_user.id, status="pending")
            .order_by(Conversation.created_at.asc())
            .first())

    if not conv:
        # 没有 pending，续用最近的 active 对话（保留历史）
        conv = (db.query(Conversation)
                .filter_by(user_id=current_user.id, status="active")
                .order_by(Conversation.created_at.desc())
                .first())

    if not conv:
        # 真的没有任何对话，才创建新的
        conv = Conversation(user_id=current_user.id, trigger="chat", status="active")
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 如果还没有任何消息，生成教练开场白
    if not conv.messages:
        activity = None
        if conv.activity_id:
            activity = db.query(Activity).filter_by(id=conv.activity_id).first()

        model_used = "fallback"
        try:
            first_msg, model_used = build_first_message(current_user, persona, db, activity, ctl, atl, tsb, provider_order)
        except Exception as e:
            first_msg = f"你好，{current_user.firstname or '运动员'}！我是你的教练 {persona.name}，跟我聊聊最近的训练吧。"
            import logging
            logging.error(f"Coach first message failed: {e}")

        msg = Message(conversation_id=conv.id, role="coach", content=first_msg)
        db.add(msg)
        conv.status = "active"
        db.commit()
        db.refresh(conv)

    # 如果没有调用 LLM（对话已有历史消息），返回配置的主力模型名作为提示
    if model_used is None:
        model_used = MODELS[settings.llm_provider][LLMTask.CHAT]

    return {
        "conversation_id": conv.id,
        "trigger": conv.trigger,
        "status": conv.status,
        "model": model_used,
        "avatar_url": persona.avatar_url,
        "topics": _conversation_topic_names(conv.id, db),
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at}
            for m in conv.messages
        ],
    }


# ── 开启新对话 ────────────────────────────────────────────

@router.post("/new")
def new_conversation(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    persona = get_or_create_persona(current_user.id, db)
    ctl, atl, tsb = _get_fitness_values(current_user.id, db)
    provider_order = _get_provider_order(current_user.id, db)

    conv = Conversation(user_id=current_user.id, trigger="chat", status="active")
    db.add(conv)
    db.commit()
    db.refresh(conv)

    model_used = "fallback"
    try:
        first_msg, model_used = build_first_message(current_user, persona, db, None, ctl, atl, tsb, provider_order)
    except Exception as e:
        first_msg = f"新对话开始！{current_user.firstname or '运动员'}，最近训练怎么样？"
        import logging
        logging.error(f"Coach first message failed: {e}")

    db.add(Message(conversation_id=conv.id, role="coach", content=first_msg))
    db.commit()
    db.refresh(conv)

    return {
        "conversation_id": conv.id,
        "model": model_used,
        "avatar_url": persona.avatar_url,
        "topics": _conversation_topic_names(conv.id, db),
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at}
            for m in conv.messages
        ],
    }


# ── 发送消息 ──────────────────────────────────────────────

class ChatInput(BaseModel):
    content: str


@router.post("/message/{conversation_id}")
def send_message(
    conversation_id: int,
    body: ChatInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = db.query(Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    if conv.user_id != current_user.id:
        raise HTTPException(403, "无权操作此对话")
    if conv.status == "complete":
        conv.status = "active"

    persona = get_or_create_persona(current_user.id, db)
    ctl, atl, tsb = _get_fitness_values(current_user.id, db)
    provider_order = _get_provider_order(current_user.id, db)

    # 存用户消息
    db.add(Message(conversation_id=conv.id, role="user", content=body.content))
    db.commit()

    try:
        reply, is_done, model_used = chat(conv, body.content, current_user, persona, db, ctl, atl, tsb, provider_order)
    except Exception as e:
        import logging
        logging.error(f"Coach chat failed: {e}")
        raise HTTPException(500, f"教练暂时无法回复：{str(e)}")

    # 存教练回复
    db.add(Message(conversation_id=conv.id, role="coach", content=reply))
    db.flush()
    db.expire(conv, ["messages"])

    # 检测用户是否在设置新身份，若是则搜索头像
    new_avatar_url = None
    try:
        persona_name = detect_persona_name(body.content)
        if persona_name:
            url = find_avatar_url(persona_name)
            if url:
                persona.avatar_url = url
                new_avatar_url = url
    except Exception:
        pass

    user_message_count = _user_message_count(conv)
    should_process_topics = (
        user_message_count > 0
        and user_message_count % TOPIC_DETECT_USER_MESSAGE_INTERVAL == 0
    )
    if should_process_topics:
        try:
            data = extract_structured_data(conv, current_user, db)
            conv.training_type = data.get("training_type")
            conv.rpe = data.get("rpe")
            conv.body_status = data.get("body_status")
            conv.life_stress = data.get("life_stress")
            conv.notes = data.get("notes")
        except Exception:
            pass
        try:
            topic_result = process_conversation_topics(
                conv,
                current_user,
                db,
                detect_recent_user_messages=TOPIC_DETECT_USER_MESSAGE_INTERVAL,
                summarize_recent_user_messages=TOPIC_SUMMARY_USER_MESSAGE_WINDOW,
            )
        except Exception as e:
            topic_result = {"topics": [], "error": f"{type(e).__name__}: {e}"}
    else:
        topic_result = {"topics": _conversation_topic_names(conv.id, db), "scheduled": True}
        _schedule_delayed_process_topics(conv.id, current_user.id, user_message_count)

    db.commit()

    return {
        "reply": reply,
        "is_complete": is_done,
        "model": model_used,
        "avatar_url": new_avatar_url,
        "topics": _conversation_topic_names(conv.id, db),
        "topic_processing": topic_result,
    }


def _schedule_delayed_process_topics(conversation_id: int, user_id: int, expected_user_message_count: int):
    timer = threading.Timer(
        TOPIC_DETECT_DELAY_SECONDS,
        _delayed_process_topics,
        args=(conversation_id, user_id, expected_user_message_count),
    )
    timer.daemon = True
    timer.start()


def _delayed_process_topics(conversation_id: int, user_id: int, expected_user_message_count: int):
    db = next(get_db())
    try:
        conv = db.query(Conversation).filter_by(id=conversation_id, user_id=user_id).first()
        user = db.query(User).filter_by(id=user_id).first()
        if not conv or not user:
            return
        if _user_message_count(conv) != expected_user_message_count:
            return
        result = process_conversation_topics(
            conv,
            user,
            db,
            detect_recent_user_messages=TOPIC_DETECT_USER_MESSAGE_INTERVAL,
            summarize_recent_user_messages=TOPIC_SUMMARY_USER_MESSAGE_WINDOW,
        )
        if result.get("error"):
            import logging
            logging.warning("Delayed topic processing result for conversation %s: %s", conversation_id, result)
        db.commit()
    finally:
        db.close()


@router.get("/conversations/{conversation_id}/model-logs")
def list_model_logs(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    if conv.user_id != current_user.id:
        raise HTTPException(403, "无权操作此对话")

    rows = (
        db.query(ModelCallLog)
        .filter_by(user_id=current_user.id, conversation_id=conversation_id)
        .order_by(ModelCallLog.created_at.desc())
        .limit(30)
        .all()
    )
    return {
        "logs": [
            {
                "id": row.id,
                "task": row.task,
                "model": row.model,
                "request": row.request_json,
                "response": row.response_text,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


@router.post("/conversations/{conversation_id}/process-topics")
def process_topics_for_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """开发测试用：手动触发当前对话的 topic 整理。"""
    conv = db.query(Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    if conv.user_id != current_user.id:
        raise HTTPException(403, "无权操作此对话")

    result = process_conversation_topics(
        conv,
        current_user,
        db,
        detect_recent_user_messages=TOPIC_DETECT_USER_MESSAGE_INTERVAL,
        summarize_recent_user_messages=TOPIC_SUMMARY_USER_MESSAGE_WINDOW,
    )
    db.commit()
    return {"conversation_id": conv.id, **result, "current_topics": _conversation_topic_names(conv.id, db)}


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
