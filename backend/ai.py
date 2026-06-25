import json
from typing import Any

import httpx


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-oss-120b"


def _extract_message_content(data: dict[str, Any]) -> str:
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


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()

    if text.startswith("```"):
        # Remove the opening fence line (e.g. "```json") then the closing fence.
        first_newline = text.find("\n")
        text = text[first_newline + 1:] if first_newline != -1 else ""
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("Structured AI response did not contain a JSON object")

    snippet = text[start : end + 1]
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in AI response: {exc}") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("Structured AI response root must be an object")

    return parsed


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
    return _extract_message_content(data)


def openrouter_board_structured_response(
    api_key: str,
    prompt: str,
    board: dict[str, Any],
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required")
    if not prompt.strip():
        raise ValueError("Prompt is required")

    safe_history: list[dict[str, str]] = []
    for entry in history or []:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role", "")
        content = entry.get("content", "")
        if role not in {"user", "assistant"}:
            continue
        if not isinstance(content, str):
            continue
        safe_history.append({"role": role, "content": content})

    system_message = {
        "role": "system",
        "content": (
            "You are a Kanban assistant. Return ONLY JSON with this exact schema: "
            '{"message": "string", "board": null or {"columns": [...], "cards": {...}}}. '
            "If no board changes are needed, set board to null. Keep message concise."
        ),
    }

    user_message = {
        "role": "user",
        "content": (
            "Current board JSON:\n"
            f"{json.dumps(board)}\n\n"
            "User request:\n"
            f"{prompt}"
        ),
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [system_message, *safe_history, user_message],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    response = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        content=json.dumps(payload),
        timeout=45.0,
    )
    response.raise_for_status()

    text = _extract_message_content(response.json())
    parsed = _extract_json_object(text)

    message = parsed.get("message")
    updated_board = parsed.get("board")

    if not isinstance(message, str) or not message.strip():
        raise RuntimeError("Structured AI response must include non-empty 'message'")

    if updated_board is not None and not isinstance(updated_board, dict):
        raise RuntimeError("Structured AI response field 'board' must be object or null")

    return {
        "message": message.strip(),
        "board": updated_board,
    }
