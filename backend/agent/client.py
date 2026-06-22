from functools import lru_cache

import anthropic

import config


@lru_cache
def get_anthropic_client() -> anthropic.Anthropic:
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("Missing ANTHROPIC_API_KEY env var")
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
