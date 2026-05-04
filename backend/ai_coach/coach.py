import json
import logging
import httpx
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from db.models import User, Activity, Conversation, CoachPersona
from ai_coach.llm import call_llm, LLMTask

logger = logging.getLogger(__name__)

DONE_SIGNAL = "[DONE]"


def get_or_create_persona(user_id: int, db: Session) -> CoachPersona:
    persona = db.query(CoachPersona).filter_by(user_id=user_id).first()
    if not persona:
        persona = CoachPersona(user_id=user_id)
        db.add(persona)
        db.commit()
        db.refresh(persona)
    return persona


def _format_activity(a: Activity) -> str:
    parts = [a.sport_type, a.name]
    if a.distance:
        if a.sport_type in ("Swim", "OpenWaterSwim"):
            parts.append(f"{int(a.distance)}m")
        else:
            parts.append(f"{a.distance/1000:.1f}km")
    if a.moving_time:
        h, m = divmod(a.moving_time // 60, 60)
        parts.append(f"{h}h{m}m" if h else f"{m}min")
    if a.tss:
        parts.append(f"TSS={int(a.tss)}")
    if a.avg_heart_rate:
        parts.append(f"均心率{int(a.avg_heart_rate)}bpm")
    return " | ".join(str(p) for p in parts if p)


def _build_system_prompt(user: User, persona: CoachPersona, db: Session,
                          activity: Activity = None, ctl=None, atl=None, tsb=None) -> str:
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent = (db.query(Activity)
              .filter(Activity.user_id == user.id, Activity.start_date >= week_ago,
                      Activity.is_excluded.is_(False))
              .order_by(Activity.start_date.desc()).limit(10).all())
    recent_str = "\n".join(f"- {_format_activity(a)}" for a in recent) or "- 近7天暂无训练"

    fitness_str = ""
    if ctl is not None:
        fitness_str = f"CTL={ctl:.1f}，ATL={atl:.1f}，TSB={tsb:+.1f}"

    thresholds = []
    if user.ftp:
        thresholds.append(f"FTP={user.ftp}W")
    if user.lthr:
        thresholds.append(f"LTHR={user.lthr}bpm")
    if user.css:
        thresholds.append(f"CSS={user.css}s/100m")
    if user.run_threshold_pace:
        m, s = divmod(int(user.run_threshold_pace), 60)
        thresholds.append(f"跑步阈值={m}'{s:02d}\"/km")

    activity_str = ""
    if activity:
        activity_str = f"\n本次待复盘的训练：\n{_format_activity(activity)}\n"

    return f"""你是{persona.name}，{persona.personality}。

运动员档案：
- 姓名：{user.firstname or '运动员'}
- 训练阈值：{', '.join(thresholds) if thresholds else '未设置'}
- 当前体能：{fitness_str or '未知'}

近7天训练记录：
{recent_str}
{activity_str}
你的职责：
1. 用自然的对话方式了解这次训练的情况：训练类型（间歇/节奏/有氧恢复/长距离）、主观感受（RPE 1-10）、身体状态（正常/疲劳/疼痛/生病）、生活干扰（工作/睡眠等）
2. 问题要融入对话，不要像填表一样逐项审问
3. 收集够了（通常3-5轮）后做简短总结和一条具体建议
4. 总结完毕后在消息末尾加上 {DONE_SIGNAL}
5. 用中文回复，口吻：{persona.style}
6. 每条消息严格不超过500个汉字，在自然停顿处截断，等对方回复后再继续"""


def build_first_message(user: User, persona: CoachPersona, db: Session,
                         activity: Activity | None = None, ctl=None, atl=None, tsb=None) -> tuple[str, str]:
    system = _build_system_prompt(user, persona, db, activity, ctl, atl, tsb)
    trigger = "帮我看看这条训练数据，生成开场白（1-2句，自然，不要说'当然'之类的废话）" if activity \
              else "主动找运动员聊聊最近状态，生成开场白（1-2句）"

    text, model = call_llm(LLMTask.CHAT, system, [{"role": "user", "content": trigger}])
    return text, model


def chat(conversation: Conversation, user_message: str,
         user: User, persona: CoachPersona, db: Session,
         ctl=None, atl=None, tsb=None) -> tuple[str, bool, str]:
    activity = None
    if conversation.activity_id:
        activity = db.query(Activity).filter_by(id=conversation.activity_id).first()

    system = _build_system_prompt(user, persona, db, activity, ctl, atl, tsb)

    history = []
    for msg in conversation.messages:
        role = "assistant" if msg.role == "coach" else "user"
        history.append({"role": role, "content": msg.content})
    history.append({"role": "user", "content": user_message})

    reply, model = call_llm(LLMTask.CHAT, system, history)
    is_done = DONE_SIGNAL in reply
    return reply.replace(DONE_SIGNAL, "").strip(), is_done, model


def find_avatar_url(name: str) -> str | None:
    """用 Wikipedia API 搜索人物头像图片 URL"""
    try:
        resp = httpx.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "titles": name,
                "prop": "pageimages",
                "format": "json",
                "pithumbsize": 300,
                "redirects": 1,
            },
            timeout=5.0,
        )
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            if "thumbnail" in page:
                return page["thumbnail"]["source"]
    except Exception as e:
        logger.warning(f"Wikipedia avatar search failed for '{name}': {e}")
    return None


def detect_persona_name(user_message: str) -> str | None:
    """检测用户消息是否在设置新身份，返回人物英文名或 None"""
    prompt = f"""判断以下消息是否在设置教练的扮演身份或角色扮演对象。如果是，提取要扮演的人物英文全名。
消息：{user_message}
只返回 JSON，格式：{{"name": "英文全名"}} 或 {{"name": null}}"""
    try:
        text, _ = call_llm(LLMTask.EXTRACT, "", [{"role": "user", "content": prompt}])
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        data = json.loads(text)
        return data.get("name")
    except Exception:
        return None


def extract_structured_data(conversation: Conversation) -> dict:
    history = "\n".join(
        f"{'教练' if m.role == 'coach' else '运动员'}：{m.content}"
        for m in conversation.messages
    )
    prompt = f"""从以下对话中提取结构化训练数据，返回 JSON：

{history}

返回格式（只返回 JSON，不要其他内容）：
{{
  "training_type": "interval|tempo|aerobic|recovery|long|unknown",
  "rpe": 数字1-10或null,
  "body_status": "normal|fatigue|pain|sick|unknown",
  "life_stress": "none|mild|significant|unknown",
  "notes": "一句话总结"
}}"""

    text, _ = call_llm(LLMTask.EXTRACT, "", [{"role": "user", "content": prompt}])
    if "```" in text:
        text = text.split("```")[1].replace("json", "").strip()
    try:
        return json.loads(text)
    except Exception:
        return {"notes": text}
