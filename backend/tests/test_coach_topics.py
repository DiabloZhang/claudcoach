import json

from db.models import (
    Conversation,
    ConversationTopic,
    InjuryConversationRef,
    Message,
    User,
    UserInjury,
    UserState,
)
from ai_coach import topics


def test_injury_topic_creates_persistent_injury_memory(db_session, monkeypatch):
    user = User(email="injury@example.com", nickname="Injured Athlete")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    conv = Conversation(user_id=user.id, trigger="chat", status="complete")
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)
    db_session.add_all([
        Message(conversation_id=conv.id, role="user", content="今天跑完左膝外侧又疼了，下坡更明显。"),
        Message(conversation_id=conv.id, role="coach", content="先降低跑量，观察两天。"),
    ])
    db_session.commit()

    def fake_call_llm(task, system, messages):
        prompt = messages[0]["content"]
        if "触发了哪些话题" in prompt:
            return json.dumps({
                "topics": [{"name": "injury", "confidence": 0.91}]
            }), "fake-model"
        return json.dumps({
            "action": "create_or_update",
            "status": "active",
            "body_part": "左膝外侧",
            "summary": "跑后左膝外侧疼痛，下坡更明显。",
            "notes": "建议暂时降低跑量并继续观察。",
            "needs_followup": True,
        }, ensure_ascii=False), "fake-model"

    monkeypatch.setattr(topics, "call_llm", fake_call_llm)

    result = topics.process_conversation_topics(conv, user, db_session)
    db_session.commit()

    assert result["topics"] == ["injury"]
    assert result["injury_saved"] is True

    topic = db_session.query(ConversationTopic).filter_by(conversation_id=conv.id).one()
    assert topic.topic == "injury"
    assert topic.confidence == 0.91

    injury = db_session.query(UserInjury).filter_by(user_id=user.id).one()
    assert injury.body_part == "左膝外侧"
    assert injury.status == "active"
    assert "下坡" in injury.summary

    ref = db_session.query(InjuryConversationRef).filter_by(injury_id=injury.id).one()
    assert ref.conversation_id == conv.id
    assert ref.ref_type == "first_mention"

    state = db_session.query(UserState).filter_by(user_id=user.id, state_key="coach_tasks").one()
    tasks = json.loads(state.state_value)
    assert tasks[0]["type"] == "injury_followup"
    assert tasks[0]["injury_id"] == injury.id


def test_injury_topic_without_body_part_still_creates_memory(db_session, monkeypatch):
    user = User(email="injury-fallback@example.com", nickname="Injured Athlete")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    conv = Conversation(user_id=user.id, trigger="chat", status="active")
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)
    db_session.add(Message(
        conversation_id=conv.id,
        role="user",
        content="最近一直有牵拉痛，但我还没说清楚具体位置。",
    ))
    db_session.commit()

    def fake_call_llm(task, system, messages):
        prompt = messages[0]["content"]
        if "触发了哪些话题" in prompt:
            return json.dumps({
                "topics": [{"name": "injury", "confidence": 0.9}]
            }), "fake-model"
        return json.dumps({
            "action": "create_or_update",
            "status": "active",
            "body_part": "",
            "summary": "用户提到持续牵拉痛，但具体部位待确认。",
            "notes": "",
            "needs_followup": False,
        }, ensure_ascii=False), "fake-model"

    monkeypatch.setattr(topics, "call_llm", fake_call_llm)

    result = topics.process_conversation_topics(conv, user, db_session)
    db_session.commit()

    assert result["topics"] == ["injury"]
    assert result["injury_saved"] is True
    injury = db_session.query(UserInjury).filter_by(user_id=user.id).one()
    assert injury.body_part == "未明确部位"


def test_injury_topic_summary_failure_creates_fallback_memory(db_session, monkeypatch):
    user = User(email="injury-error@example.com", nickname="Injured Athlete")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    conv = Conversation(user_id=user.id, trigger="chat", status="active")
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)
    db_session.add(Message(
        conversation_id=conv.id,
        role="user",
        content="左腿后侧痛了十个月，比赛后更明显。",
    ))
    db_session.commit()

    def fake_call_llm(task, system, messages):
        prompt = messages[0]["content"]
        if "触发了哪些话题" in prompt:
            return json.dumps({
                "topics": [{"name": "injury", "confidence": 0.95}]
            }), "fake-model"
        raise RuntimeError("summary model unavailable")

    monkeypatch.setattr(topics, "call_llm", fake_call_llm)

    result = topics.process_conversation_topics(conv, user, db_session)
    db_session.commit()

    assert result["topics"] == ["injury"]
    assert result["injury_saved"] is True
    assert "injury_processing_failed" in result["error"]
    injury = db_session.query(UserInjury).filter_by(user_id=user.id).one()
    assert injury.body_part == "未明确部位"
    assert "自动总结失败" in injury.notes
