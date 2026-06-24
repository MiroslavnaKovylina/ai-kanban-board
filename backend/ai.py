import json

import httpx


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-oss-120b"


def openrouter_sanity_check(api_key: str) -> str:
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required")

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "What is 2+2? Reply with just the answer."},
        ],
        "temperature": 0,
    }

    response = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        content=json.dumps(payload),
        timeout=30.0,
    )
    response.raise_for_status()

    data = response.json()
    choices = data.get("choices")
    if not choices:
        raise RuntimeError("OpenRouter response missing choices")

    message = choices[0].get("message", {})
    content = message.get("content")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
        merged = " ".join(part for part in text_parts if part).strip()
        if merged:
            return merged

    raise RuntimeError("OpenRouter response missing message content")
