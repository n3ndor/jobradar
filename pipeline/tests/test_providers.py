import httpx
import pytest
import respx

from pipeline import providers
from pipeline.providers import KeyDenied, select_provider


def test_select_provider_prefers_groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza_x")
    name, model, key, _ = select_provider()
    assert name == "groq"
    assert key == "gsk_x"


def test_select_provider_falls_back_to_gemini(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "AIza_x")
    name, *_ = select_provider()
    assert name == "gemini"


def test_select_provider_none_without_keys(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert select_provider() is None


async def test_groq_call_parses_response():
    payload = {
        "choices": [
            {"message": {"content": '{"summary":"A backend role","salary_min":80000,'
                                    '"salary_max":100000,"salary_currency":"EUR"}'}}
        ],
        "usage": {"total_tokens": 123},
    }
    with respx.mock(assert_all_called=False) as router:
        router.post(providers.GROQ_ENDPOINT).mock(return_value=httpx.Response(200, json=payload))
        with httpx.Client() as client:
            result, tokens = providers._call_groq(client, "gsk_x", "prompt")
    assert result.summary == "A backend role"
    assert result.salary_min == 80000
    assert result.salary_currency == "EUR"
    assert tokens == 123


async def test_groq_call_raises_keydenied_on_401():
    with respx.mock(assert_all_called=False) as router:
        router.post(providers.GROQ_ENDPOINT).mock(
            return_value=httpx.Response(401, json={"error": "bad key"})
        )
        with httpx.Client() as client:
            with pytest.raises(KeyDenied):
                providers._call_groq(client, "gsk_bad", "prompt")


async def test_gemini_call_parses_response():
    payload = {
        "candidates": [
            {"content": {"parts": [{"text": '{"summary":"A role","salary_min":null,'
                                            '"salary_max":null,"salary_currency":null}'}]}}
        ],
        "usageMetadata": {"totalTokenCount": 55},
    }
    with respx.mock(assert_all_called=False) as router:
        router.post(url__startswith="https://generativelanguage.googleapis.com").mock(
            return_value=httpx.Response(200, json=payload)
        )
        with httpx.Client() as client:
            result, tokens = providers._call_gemini(client, "AIza_x", "prompt")
    assert result.summary == "A role"
    assert result.salary_min is None
    assert tokens == 55
