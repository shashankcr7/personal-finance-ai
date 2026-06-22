import json

from agent import categorizer


class FakeContentBlock:
    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeContentBlock(text)]


class FakeMessages:
    def __init__(self, response_text):
        self._response_text = response_text

    def create(self, **kwargs):
        return FakeResponse(self._response_text)


class FakeAnthropicClient:
    def __init__(self, response_text):
        self.messages = FakeMessages(response_text)


def test_categorize_unmatched_accepts_valid_category(monkeypatch):
    fake_client = FakeAnthropicClient(json.dumps({"SWIGGY": "Food & Dining"}))
    monkeypatch.setattr(categorizer, "get_anthropic_client", lambda: fake_client)

    result = categorizer.categorize_unmatched(
        merchants=["SWIGGY"],
        category_names=["Food & Dining", "Transport"],
        few_shot=[],
    )

    assert result == {"SWIGGY": "Food & Dining"}


def test_categorize_unmatched_rejects_hallucinated_category(monkeypatch):
    fake_client = FakeAnthropicClient(json.dumps({"SWIGGY": "Made Up Category"}))
    monkeypatch.setattr(categorizer, "get_anthropic_client", lambda: fake_client)

    result = categorizer.categorize_unmatched(
        merchants=["SWIGGY"],
        category_names=["Food & Dining", "Transport"],
        few_shot=[],
    )

    assert result == {"SWIGGY": None}


def test_categorize_unmatched_strips_markdown_code_fence(monkeypatch):
    fenced_response = '```json\n{"SWIGGY": "Food & Dining"}\n```'
    fake_client = FakeAnthropicClient(fenced_response)
    monkeypatch.setattr(categorizer, "get_anthropic_client", lambda: fake_client)

    result = categorizer.categorize_unmatched(
        merchants=["SWIGGY"],
        category_names=["Food & Dining", "Transport"],
        few_shot=[],
    )

    assert result == {"SWIGGY": "Food & Dining"}


def test_categorize_unmatched_handles_unparseable_response(monkeypatch):
    fake_client = FakeAnthropicClient("not valid json")
    monkeypatch.setattr(categorizer, "get_anthropic_client", lambda: fake_client)

    result = categorizer.categorize_unmatched(
        merchants=["SWIGGY", "UBER"],
        category_names=["Food & Dining", "Transport"],
        few_shot=[],
    )

    assert result == {"SWIGGY": None, "UBER": None}


def test_categorize_unmatched_empty_input_short_circuits():
    assert categorizer.categorize_unmatched([], ["Food & Dining"], []) == {}
