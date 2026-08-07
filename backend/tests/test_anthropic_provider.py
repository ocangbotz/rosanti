import httpx
import pytest

from app.config import Settings
from app.core.exceptions import AIProviderError
from app.services.ai.anthropic_provider import ANTHROPIC_API_URL, AnthropicProvider


def _settings(**overrides) -> Settings:
    defaults = {
        "anthropic_api_key": "sk-ant-test-key",
        "anthropic_model": "claude-test-text",
        "anthropic_vision_model": "claude-test-vision",
    }
    defaults.update(overrides)
    return Settings(**defaults)


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self) -> dict:
        return self._json_data


class _FakeAsyncClient:
    response_to_return: _FakeResponse | Exception = _FakeResponse(200, {"content": []})
    last_call: dict | None = None

    def __init__(self, timeout=None):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, headers=None, json=None):
        _FakeAsyncClient.last_call = {"url": url, "headers": headers, "json": json}
        if isinstance(_FakeAsyncClient.response_to_return, Exception):
            raise _FakeAsyncClient.response_to_return
        return _FakeAsyncClient.response_to_return


@pytest.fixture(autouse=True)
def patch_httpx_client(monkeypatch):
    monkeypatch.setattr("app.services.ai.anthropic_provider.httpx.AsyncClient", _FakeAsyncClient)
    yield


def test_missing_api_key_raises_immediately():
    with pytest.raises(AIProviderError):
        AnthropicProvider(_settings(anthropic_api_key=None))


@pytest.mark.asyncio
async def test_generate_text_sends_correct_payload_and_parses_response():
    _FakeAsyncClient.response_to_return = _FakeResponse(
        200, {"content": [{"type": "text", "text": "Bullish structure with confirmed BOS."}]}
    )
    provider = AnthropicProvider(_settings())

    result = await provider.generate_text("system prompt", "user prompt", max_tokens=256)

    assert result == "Bullish structure with confirmed BOS."
    call = _FakeAsyncClient.last_call
    assert call["url"] == ANTHROPIC_API_URL
    assert call["headers"]["x-api-key"] == "sk-ant-test-key"
    assert call["json"]["model"] == "claude-test-text"
    assert call["json"]["system"] == "system prompt"
    assert call["json"]["messages"][0]["content"] == [{"type": "text", "text": "user prompt"}]
    assert call["json"]["max_tokens"] == 256


@pytest.mark.asyncio
async def test_generate_vision_encodes_image_and_uses_vision_model():
    _FakeAsyncClient.response_to_return = _FakeResponse(
        200, {"content": [{"type": "text", "text": '{"ok": true}'}]}
    )
    provider = AnthropicProvider(_settings())

    result = await provider.generate_vision(
        "system prompt", "describe this chart", b"\x89PNG\r\n", "image/png"
    )

    assert result == '{"ok": true}'
    call = _FakeAsyncClient.last_call
    assert call["json"]["model"] == "claude-test-vision"
    content_blocks = call["json"]["messages"][0]["content"]
    assert content_blocks[0]["type"] == "image"
    assert content_blocks[0]["source"]["media_type"] == "image/png"
    assert content_blocks[1] == {"type": "text", "text": "describe this chart"}


@pytest.mark.asyncio
async def test_non_200_response_raises_ai_provider_error():
    _FakeAsyncClient.response_to_return = _FakeResponse(500, text="internal error")
    provider = AnthropicProvider(_settings())

    with pytest.raises(AIProviderError):
        await provider.generate_text("s", "u")


@pytest.mark.asyncio
async def test_network_error_raises_ai_provider_error():
    _FakeAsyncClient.response_to_return = httpx.ConnectTimeout("timed out")
    provider = AnthropicProvider(_settings())

    with pytest.raises(AIProviderError):
        await provider.generate_text("s", "u")


@pytest.mark.asyncio
async def test_empty_content_raises_ai_provider_error():
    _FakeAsyncClient.response_to_return = _FakeResponse(200, {"content": []})
    provider = AnthropicProvider(_settings())

    with pytest.raises(AIProviderError):
        await provider.generate_text("s", "u")
