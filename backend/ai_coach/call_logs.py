import logging

from sqlalchemy.orm import Session

from ai_coach.llm import LLMTask
from db.models import ModelCallLog

logger = logging.getLogger(__name__)


def log_model_call(
    db: Session,
    user_id: int,
    conversation_id: int | None,
    task: LLMTask,
    model: str,
    system: str,
    messages: list[dict],
    response_text: str,
) -> None:
    try:
        db.add(ModelCallLog(
            user_id=user_id,
            conversation_id=conversation_id,
            task=task.value,
            model=model,
            request_json={
                "system": system,
                "messages": messages,
            },
            response_text=response_text,
        ))
    except Exception as e:
        logger.warning("Failed to log model call: %s", e)
