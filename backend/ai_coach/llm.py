"""
统一 LLM 调用层
- 三档任务：THINK / CHAT / EXTRACT
- 优先 Gemini，失败自动切 Claude
"""
import logging
from enum import Enum
import anthropic
from google import genai
from google.genai import types as genai_types
from config import settings

logger = logging.getLogger(__name__)


class LLMTask(Enum):
    THINK = "think"      # 训练计划、周月总结、深度建议
    CHAT = "chat"        # 教练日常对话、训练复盘
    EXTRACT = "extract"  # 结构化数据提取、日志生成


# 各档任务的模型映射
MODELS = {
    "gemini": {
        LLMTask.THINK:   "gemini-3-pro-preview",
        LLMTask.CHAT:    "gemini-2.5-flash",
        LLMTask.EXTRACT: "gemini-2.5-flash",
    },
    "anthropic": {
        LLMTask.THINK:   "claude-sonnet-4-6",
        LLMTask.CHAT:    "claude-sonnet-4-6",
        LLMTask.EXTRACT: "claude-haiku-4-5-20251001",
    },
}

MAX_TOKENS = {
    LLMTask.THINK:   2000,
    LLMTask.CHAT:    1800,
    LLMTask.EXTRACT: 300,
}


def _call_gemini(task: LLMTask, system: str, messages: list[dict]) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    model = MODELS["gemini"][task]

    # Gemini 要求对话必须以 user 开头，过滤掉开头的 assistant 消息
    filtered = list(messages)
    while filtered and filtered[0]["role"] != "user":
        filtered = filtered[1:]
    if not filtered:
        filtered = messages[-1:]  # 至少保留最后一条

    contents = []
    for msg in filtered:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(genai_types.Content(
            role=role,
            parts=[genai_types.Part(text=msg["content"])]
        ))

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=genai_types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=MAX_TOKENS[task],
        ),
    )
    return response.text


def _call_anthropic(task: LLMTask, system: str, messages: list[dict]) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    model = MODELS["anthropic"][task]

    resp = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS[task],
        system=system,
        messages=messages,
    )
    return resp.content[0].text


def call_llm(
    task: LLMTask,
    system: str,
    messages: list[dict],
    provider_order: list[str] | None = None,
) -> tuple[str, str]:
    """
    统一调用入口。优先用 settings.llm_provider，失败自动切另一个。
    返回 (reply_text, model_name_used)
    """
    if provider_order:
        order = [p for p in provider_order if p in ("gemini", "anthropic")]
    else:
        order = [settings.llm_provider] if settings.llm_provider in ("gemini", "anthropic") else []
    for provider in ("gemini", "anthropic"):
        if provider not in order:
            order.append(provider)

    callers = {
        "gemini": _call_gemini,
        "anthropic": _call_anthropic,
    }

    last_error = None
    for idx, provider in enumerate(order):
        try:
            text = callers[provider](task, system, messages)
            return text, MODELS[provider][task]
        except Exception as e:
            last_error = e
            label = "primary" if idx == 0 else "fallback"
            logger.error(f"LLM {label} ({provider}/{MODELS[provider][task]}) failed: {e}")
    raise RuntimeError(f"所有 LLM provider 均不可用：{last_error}")
