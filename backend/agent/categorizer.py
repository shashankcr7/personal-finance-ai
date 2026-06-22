import json

from .client import get_anthropic_client

CATEGORIZER_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = (
    "You are a bank transaction categorization assistant for a personal finance app. "
    "You only categorize text descriptions; you never compute or report any monetary amount. "
    "Choose exactly one category from the provided list for each merchant, or null if none fit. "
    "Respond with ONLY a JSON object mapping each merchant string to a category name or null. "
    "No prose, no markdown, no explanation."
)


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def categorize_unmatched(
    merchants: list[str],
    category_names: list[str],
    few_shot: list[tuple[str, str]],
) -> dict[str, str | None]:
    if not merchants:
        return {}

    few_shot_lines = (
        "\n".join(f'- "{merchant}" -> "{category}"' for merchant, category in few_shot)
        or "(none yet)"
    )
    merchant_lines = "\n".join(f'- "{merchant}"' for merchant in merchants)

    user_message = (
        f"Allowed categories: {json.dumps(category_names)}\n\n"
        f"Examples of how this household has categorized merchants before:\n{few_shot_lines}\n\n"
        f"Categorize these merchants:\n{merchant_lines}"
    )

    client = get_anthropic_client()
    response = client.messages.create(
        model=CATEGORIZER_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    try:
        parsed = json.loads(_strip_markdown_fence(response.content[0].text))
    except (json.JSONDecodeError, IndexError, AttributeError):
        parsed = None

    valid_names = {name.lower(): name for name in category_names}
    result: dict[str, str | None] = {}
    for merchant in merchants:
        guess = parsed.get(merchant) if isinstance(parsed, dict) else None
        if isinstance(guess, str) and guess.lower() in valid_names:
            result[merchant] = valid_names[guess.lower()]
        else:
            result[merchant] = None
    return result
