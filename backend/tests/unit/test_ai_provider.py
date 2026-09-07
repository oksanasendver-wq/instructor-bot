import pytest
import httpx
from app.services.ai_provider import AIProvider


def test_prompt_contains_structured_facts_not_fake_scores():
    prompt = AIProvider()._build_prompt(
        {
            "scores": {"city": {"score": 72}},
            "reports": [{"comment_internal": "Отработать зеркала"}],
        }
    )
    assert "72" in prompt and "зеркала" in prompt
    assert "не утверждай" in prompt


def test_hash_changes_when_comments_change():
    provider = AIProvider()
    assert provider._calculate_hash({"comment": "a"}) != provider._calculate_hash(
        {"comment": "b"}
    )
    assert provider._calculate_hash({"a": 1, "b": 2}) == provider._calculate_hash(
        {"b": 2, "a": 1}
    )


@pytest.mark.asyncio
async def test_missing_key_fails_without_network():
    with pytest.raises(ValueError, match="не настроен"):
        await AIProvider("groq", "").generate_conclusion_draft({})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,expected", [("groq", "api.groq.com"), ("nvidia", "integrate.api.nvidia.com")]
)
async def test_both_adapters_send_and_parse(monkeypatch, name, expected):
    calls = []

    async def post(self, url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Проверенный черновик"}}],
                "model": "test-model",
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    result = await AIProvider(name, "test-key").generate_conclusion_draft({"score": 70})
    assert expected in calls[0][0]
    assert result["text"] == "Проверенный черновик"
    assert result["model"] == "test-model"
