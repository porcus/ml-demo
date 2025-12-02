import os
from openai import OpenAI
from typing import Literal

Provider = Literal["openai", "lmstudio"]


# --- Clients ---

# Remote OpenAI (cloud)
_openai_client: OpenAI | None
if not os.getenv("OPENAI_API_KEY", "-") == "-": _openai_client = OpenAI()  # uses OPENAI_API_KEY from env

# LM Studio (local, OpenAI-compatible API)
# - Make sure LM Studio's server is running on localhost:1234 (Developer tab -> Start server)
# - "api_key" can be any string; LM Studio doesn't actually validate it
_lmstudio_client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key=os.getenv("LMSTUDIO_API_KEY", "lm-studio"),
)


def _build_messages(user_text: str) -> list[dict]:
    """
    Shared helper to build the messages list for chat.completions.create().
    """
    return [
        {
            "role": "system",
            "content": (
                "You are a concise assistant that summarizes text for busy senior engineers. "
                "Keep summaries short and focused on key points."
            ),
        },
        {"role": "user", "content": user_text},
    ]


def summarize_with_openai(text: str) -> str:
    """
    Use OpenAI's hosted models via chat.completions.create().
    """
    messages = _build_messages(text)

    response = _openai_client.chat.completions.create(
        model="gpt-4o-mini",  # or gpt-4.1-mini, etc.
        messages=messages,
        max_tokens=256,
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()


def summarize_with_lmstudio(text: str, model: str) -> str:
    """
    Use a local model served by LM Studio via its OpenAI-compatible endpoint.

    `model` should match the identifier shown in LM Studio's Local Server tab,
    e.g. "lmstudio-community/qwen2.5-7b-instruct" or similar.
    """
    messages = _build_messages(text)

    response = _lmstudio_client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=256,
        temperature=0.4,
    )

    return response.choices[0].message.content.strip()


def summarize_text(text: str, provider: Provider = "lmstudio", lmstudio_model: str | None = None) -> str:
    """
    Main entry point used by your FastAPI route.
    Provider should be "lmstudio" or "openai"
    """

    if provider == "lmstudio":
        if not lmstudio_model:
            raise ValueError("lmstudio_model is required when provider='lmstudio'")
        return summarize_with_lmstudio(text, model=lmstudio_model)

    return summarize_with_openai(text)
