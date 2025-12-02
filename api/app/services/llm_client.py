import os
from functools import lru_cache
from typing import Optional

from openai import OpenAI


# Defaults for LM Studio's OpenAI-compatible API
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "qwen/qwen3-vl-8b")


@lru_cache(maxsize=1)
def get_lm_client() -> OpenAI:
    """
    Returns a singleton OpenAI-compatible client configured for LM Studio.

    LM Studio typically ignores the API key, but the OpenAI client requires one,
    so we just pass a dummy string.
    """
    client = OpenAI(
        base_url=LMSTUDIO_BASE_URL,
        api_key=os.getenv("LMSTUDIO_API_KEY", "lmstudio-placeholder-key"),
    )
    return client