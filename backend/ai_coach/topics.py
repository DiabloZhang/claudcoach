import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from ai_coach.call_logs import log_model_call
from ai_coach.llm import LLMTask, call_llm
from db.models import (
    Conversation,
    ConversationTopic,
    InjuryConversationRef,
    User,
    UserInjury,
    UserState,
)

logger = logging.getLogger(__name__)

ACTIVE_INJURY_STATUSES = ("active", "recovering")
COACH_TASKS_KEY = "coach_tasks"


def _conversation_text(conversation: Conversation, recent_user_messages: int | None = None) -> str:
    messages = list(conversation.messages)
    if recent_user_messages:
        user_seen = 0
        start_idx = 0
        for idx in range(len(messages) - 1, -1, -1):
            if messages[idx].role == "user":
                user_seen += 1
                if user_seen == recent_user_messages:
                    start_idx = idx
                    break
        messages = messages[start_idx:]
    return "\n".join(
        f"{'教练' if m.role == 'coach' else '运动员'}：{m.content}"
        for m in messages
    )


def _parse_json_object(text: str) -> dict:
    cleaned = text.strip()
    if "```" in cleaned:
        cleaned = cleaned.split("```")[1].replace("json", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def _active_injuries(user_id: int, db: Session) -> list[UserInjury]:
    return (
        db.query(UserInjury)
        .filter(UserInjury.user_id == user_id, UserInjury.status.in_(ACTIVE_INJURY_STATUSES))
        .order_by(UserInjury.updated_at.desc())
        .all()
    )


def format_active_injuries(user_id: int, db: Session) -> str:
    injuries = _active_injuries(user_id, db)
    if not injuries:
        return ""
    lines = []
    for injury in injuries:
        parts = [
            f"- {injury.body_part}",
            f"状态：{injury.status}",
        ]
        if injury.summary:
            parts.append(f"摘要：{injury.summary}")
        if injury.notes:
            parts.append(f"备注：{injury.notes}")
        lines.append("；".join(parts))
    return "\n".join(lines)


def detect_topics(
    conversation: Conversation,
    user: User,
    db: Session,
    recent_user_messages: int | None = None,
) -> list[dict]:
    history = _conversation_text(conversation, recent_user_messages)
    if not history.strip():
        return []

    prompt = f"""判断以下教练与运动员对话触发了哪些话题。只做轻量分类，不要提取细节。

当前可选 topics：
- injury：伤病、疼痛、不适、影响训练的身体问题或康复
- recovery：疲劳、睡眠、恢复、营养、压力
- schedule：日程、工作生活协调、训练时间冲突
- goal：目标赛事、赛季目标、阶段目标

对话：
{history}

只返回 JSON：
{{
  "topics": [
    {{"name": "injury", "confidence": 0.0到1.0}}
  ]
}}
如果没有明确话题，返回 {{"topics": []}}。"""

    messages = [{"role": "user", "content": prompt}]
    text, model = call_llm(LLMTask.EXTRACT, "", messages)
    log_model_call(db, user.id, conversation.id, LLMTask.EXTRACT, model, "", messages, text)
    data = _parse_json_object(text)
    topics = data.get("topics") or []
    return [
        {
            "name": str(t.get("name", "")).strip(),
            "confidence": float(t.get("confidence", 0) or 0),
        }
        for t in topics
        if t.get("name")
    ]


def summarize_injury_topic(
    conversation: Conversation,
    user: User,
    db: Session,
    recent_user_messages: int | None = None,
) -> dict:
    history = _conversation_text(conversation, recent_user_messages)
    existing = format_active_injuries(user.id, db) or "无"
    prompt = f"""从以下对话中整理伤病 topic 的最小记录。不要做医学诊断，只提炼教练后续需要持续跟进的信息。

当前活跃伤病记录：
{existing}

本轮对话：
{history}

只返回 JSON：
{{
  "action": "create_or_update|resolve|none",
  "status": "active|recovering|resolved",
  "body_part": "最具体的身体部位；没有则为空字符串",
  "summary": "一句话说明当前伤病状态",
  "notes": "其他重要细节，包含诱因、训练影响、用户主观感受、恢复建议等；没有则为空字符串",
  "needs_followup": true或false
}}"""

    messages = [{"role": "user", "content": prompt}]
    text, model = call_llm(LLMTask.EXTRACT, "", messages)
    log_model_call(db, user.id, conversation.id, LLMTask.EXTRACT, model, "", messages, text)
    data = _parse_json_object(text)
    return {
        "action": data.get("action") or "none",
        "status": data.get("status") or "active",
        "body_part": (data.get("body_part") or "").strip(),
        "summary": (data.get("summary") or "").strip(),
        "notes": (data.get("notes") or "").strip(),
        "needs_followup": bool(data.get("needs_followup")),
    }


def _find_matching_injury(user_id: int, body_part: str, db: Session) -> UserInjury | None:
    normalized = (body_part or "").strip().lower()
    if not normalized:
        return None
    injuries = _active_injuries(user_id, db)
    for injury in injuries:
        existing = (injury.body_part or "").strip().lower()
        if existing == normalized or existing in normalized or normalized in existing:
            return injury
    return None


def upsert_user_injury(user: User, conversation: Conversation, update: dict, db: Session) -> UserInjury | None:
    action = update.get("action")
    body_part = update.get("body_part")
    if action == "none" or not body_part:
        return None

    injury = _find_matching_injury(user.id, body_part, db)
    is_new = injury is None
    if is_new:
        injury = UserInjury(user_id=user.id, body_part=body_part)
        db.add(injury)

    injury.status = update.get("status") or injury.status or "active"
    injury.summary = update.get("summary") or injury.summary
    injury.notes = update.get("notes") or injury.notes
    injury.updated_at = datetime.utcnow()
    db.flush()

    if injury.status == "resolved" or action == "resolve":
        ref_type = "resolution"
    else:
        ref_type = "first_mention" if is_new else "followup"

    exists = (
        db.query(InjuryConversationRef)
        .filter_by(injury_id=injury.id, conversation_id=conversation.id, ref_type=ref_type)
        .first()
    )
    if not exists:
        db.add(InjuryConversationRef(
            injury_id=injury.id,
            conversation_id=conversation.id,
            ref_type=ref_type,
        ))

    if update.get("needs_followup") and injury.status != "resolved":
        ensure_injury_followup_task(user.id, injury, db)

    return injury


def ensure_injury_followup_task(user_id: int, injury: UserInjury, db: Session) -> None:
    state = (
        db.query(UserState)
        .filter_by(user_id=user_id, state_key=COACH_TASKS_KEY)
        .first()
    )
    if state:
        try:
            tasks = json.loads(state.state_value)
        except Exception:
            tasks = []
    else:
        tasks = []
        state = UserState(user_id=user_id, state_key=COACH_TASKS_KEY, state_value="[]")
        db.add(state)

    for task in tasks:
        if (
            task.get("type") == "injury_followup"
            and task.get("injury_id") == injury.id
            and task.get("status") == "open"
        ):
            return

    tasks.append({
        "type": "injury_followup",
        "status": "open",
        "injury_id": injury.id,
        "title": f"跟进{injury.body_part}恢复情况",
        "created_at": datetime.utcnow().isoformat(),
    })
    state.state_value = json.dumps(tasks, ensure_ascii=False)


def process_conversation_topics(
    conversation: Conversation,
    user: User,
    db: Session,
    detect_recent_user_messages: int | None = None,
    summarize_recent_user_messages: int | None = None,
) -> list[str]:
    try:
        topics = detect_topics(conversation, user, db, detect_recent_user_messages)
    except Exception as e:
        logger.warning("Topic detection failed for conversation %s: %s", conversation.id, e)
        return []

    touched = []
    db.query(ConversationTopic).filter_by(conversation_id=conversation.id).delete()
    for topic in topics:
        name = topic["name"]
        confidence = topic["confidence"]
        if confidence < 0.5:
            continue
        db.add(ConversationTopic(
            conversation_id=conversation.id,
            topic=name,
            confidence=confidence,
        ))
        touched.append(name)

    if "injury" in touched:
        try:
            update = summarize_injury_topic(conversation, user, db, summarize_recent_user_messages)
            upsert_user_injury(user, conversation, update, db)
        except Exception as e:
            logger.warning("Injury topic processing failed for conversation %s: %s", conversation.id, e)

    return touched
