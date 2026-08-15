from unittest.mock import MagicMock, patch

import pytest

from llm.base import LLMUnavailableError
from llm.groq_provider import GroqProvider


def test_no_api_key_means_unavailable():
    provider = GroqProvider(api_key=None, model="m", fallback_model="fb")
    assert provider.is_available is False


def test_chat_raises_when_unavailable():
    provider = GroqProvider(api_key=None, model="m", fallback_model="fb")
    with pytest.raises(LLMUnavailableError):
        provider.chat([{"role": "user", "content": "hi"}])


def _make_completion(text: str):
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content=text))]
    return completion


@patch("groq.Groq")
def test_chat_success_on_primary_model(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_completion("hello there")
    mock_groq_cls.return_value = mock_client

    provider = GroqProvider(api_key="fake-key", model="primary", fallback_model="fallback")
    result = provider.chat([{"role": "user", "content": "hi"}])

    assert result == "hello there"
    assert mock_client.chat.completions.create.call_count == 1


@patch("groq.Groq")
def test_chat_falls_back_to_secondary_model_on_error(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        Exception("primary failed"),
        _make_completion("fallback reply"),
    ]
    mock_groq_cls.return_value = mock_client

    provider = GroqProvider(api_key="fake-key", model="primary", fallback_model="fallback")
    result = provider.chat([{"role": "user", "content": "hi"}])

    assert result == "fallback reply"
    assert mock_client.chat.completions.create.call_count == 2


@patch("groq.Groq")
def test_chat_raises_llm_unavailable_when_all_models_fail(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("down")
    mock_groq_cls.return_value = mock_client

    provider = GroqProvider(api_key="fake-key", model="primary", fallback_model="fallback")
    with pytest.raises(LLMUnavailableError):
        provider.chat([{"role": "user", "content": "hi"}])
