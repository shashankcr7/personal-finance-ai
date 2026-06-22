from datetime import date
from decimal import Decimal

from agent import chat as chat_agent


class FakeContentBlock:
    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeContentBlock(text)]


class FakeMessages:
    def __init__(self, response_text):
        self._response_text = response_text
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeResponse(self._response_text)


class FakeAnthropicClient:
    def __init__(self, response_text):
        self.messages = FakeMessages(response_text)


REQUIRED_GUARDRAIL_KEYWORDS = [
    "arithmetic",
    "buy",
    "sell",
    "allocat",
    "assumption",
    "projection",
]


def test_system_prompt_contains_required_guardrail_keywords():
    lowered = chat_agent.SYSTEM_PROMPT.lower()
    for keyword in REQUIRED_GUARDRAIL_KEYWORDS:
        assert keyword in lowered


def test_financial_summary_returns_json_safe_dict(conn, test_user_id):
    summary_dict = chat_agent.financial_summary(
        conn, test_user_id, date.today().replace(day=1)
    )

    def assert_json_safe(value):
        if isinstance(value, dict):
            for v in value.values():
                assert_json_safe(v)
        elif isinstance(value, (list, tuple)):
            for v in value:
                assert_json_safe(v)
        else:
            assert not isinstance(value, Decimal)
            assert not isinstance(value, date)

    assert_json_safe(summary_dict)


def test_chat_embeds_financial_summary_in_system_prompt(monkeypatch, conn, test_user_id):
    fake_client = FakeAnthropicClient("Here's a narration of your numbers.")
    monkeypatch.setattr(chat_agent, "get_anthropic_client", lambda: fake_client)
    monkeypatch.setattr(
        chat_agent, "financial_summary", lambda conn, user_id, month: {"marker": "UNIQUE_VALUE_123"}
    )

    chat_agent.chat(conn, test_user_id, "Where am I losing money?", [])

    assert "UNIQUE_VALUE_123" in fake_client.messages.last_kwargs["system"]


def test_chat_returns_claude_response_text_verbatim(monkeypatch, conn, test_user_id):
    fake_client = FakeAnthropicClient("You spent more this month. ```not stripped```")
    monkeypatch.setattr(chat_agent, "get_anthropic_client", lambda: fake_client)
    monkeypatch.setattr(chat_agent, "financial_summary", lambda conn, user_id, month: {})

    result = chat_agent.chat(conn, test_user_id, "Where am I losing money?", [])

    assert result == "You spent more this month. ```not stripped```"


def test_chat_caps_history_to_max_messages(monkeypatch, conn, test_user_id):
    fake_client = FakeAnthropicClient("ok")
    monkeypatch.setattr(chat_agent, "get_anthropic_client", lambda: fake_client)
    monkeypatch.setattr(chat_agent, "financial_summary", lambda conn, user_id, month: {})

    long_history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg-{i}"}
        for i in range(30)
    ]

    chat_agent.chat(conn, test_user_id, "new question", long_history)

    sent_messages = fake_client.messages.last_kwargs["messages"]
    assert len(sent_messages) == chat_agent.MAX_HISTORY_MESSAGES + 1
    assert sent_messages[-1] == {"role": "user", "content": "new question"}
    assert sent_messages[0]["content"] == "msg-10"


def test_chat_drops_malformed_history_roles(monkeypatch, conn, test_user_id):
    fake_client = FakeAnthropicClient("ok")
    monkeypatch.setattr(chat_agent, "get_anthropic_client", lambda: fake_client)
    monkeypatch.setattr(chat_agent, "financial_summary", lambda conn, user_id, month: {})

    history = [
        {"role": "user", "content": "valid"},
        {"role": "system", "content": "should be dropped"},
        {"role": "bogus", "content": "should also be dropped"},
    ]

    chat_agent.chat(conn, test_user_id, "new question", history)

    sent_messages = fake_client.messages.last_kwargs["messages"]
    assert sent_messages == [
        {"role": "user", "content": "valid"},
        {"role": "user", "content": "new question"},
    ]
