from typing import Any
from collections import defaultdict, deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from threading import Lock
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles

from ai import openrouter_board_structured_response, openrouter_sanity_check

from db import (
    authenticate_user,
    get_board_for_user,
    get_db_connection,
    load_board,
    register_user,
    replace_board,
)

app = FastAPI(title="PM MVP Backend")

_ai_guard_lock = Lock()
_ai_minute_windows: dict[str, deque[float]] = defaultdict(deque)
_ai_daily_usage: dict[str, tuple[str, int]] = {}


def _get_int_env(name: str, default: int, minimum: int = 0) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return max(value, minimum)


def _allowed_ai_origins() -> set[str]:
    configured = os.getenv(
        "AI_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
    )
    return {item.strip().rstrip("/") for item in configured.split(",") if item.strip()}


def _normalize_origin(header_value: str) -> str:
    parsed = urlparse(header_value)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return header_value.strip().rstrip("/")


def _validate_ai_origin(origin: str | None, referer: str | None) -> tuple[bool, str]:
    # Non-browser clients often do not send Origin/Referer. Allow these requests.
    if not origin and not referer:
        return True, ""

    allowed = _allowed_ai_origins()

    for header_name, header_value in (("Origin", origin), ("Referer", referer)):
        if not header_value:
            continue
        normalized = _normalize_origin(header_value)
        if normalized not in allowed:
            return False, f"Invalid {header_name.lower()} for AI endpoint"

    return True, ""


def _check_and_consume_ai_rate_limit(ip_address: str) -> tuple[bool, str, int | None]:
    per_minute_limit = _get_int_env("AI_RATE_LIMIT_PER_MINUTE", 20, minimum=1)
    daily_limit = _get_int_env("AI_DAILY_IP_LIMIT", 0, minimum=0)

    now = time.time()
    minute_cutoff = now - 60
    today = datetime.now(timezone.utc).date().isoformat()

    with _ai_guard_lock:
        window = _ai_minute_windows[ip_address]
        while window and window[0] <= minute_cutoff:
            window.popleft()

        if len(window) >= per_minute_limit:
            retry_after = max(1, int(window[0] + 60 - now))
            return False, "Rate limit exceeded for AI endpoint. Please retry shortly.", retry_after

        if daily_limit > 0:
            usage_day, usage_count = _ai_daily_usage.get(ip_address, (today, 0))
            if usage_day != today:
                usage_day = today
                usage_count = 0

            if usage_count >= daily_limit:
                return False, "Daily AI usage limit reached for this IP.", None

            _ai_daily_usage[ip_address] = (usage_day, usage_count + 1)

        window.append(now)

    return True, "", None


def _reset_ai_guards_for_tests() -> None:
    with _ai_guard_lock:
        _ai_minute_windows.clear()
        _ai_daily_usage.clear()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_project_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


@app.on_event("startup")
def startup() -> None:
    _load_project_env()
    get_db_connection()


@app.get("/api/ping")
async def ping():
    return {"success": True, "message": "pong"}


class AuthRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class BoardPayload(BaseModel):
    columns: list[dict[str, Any]]
    cards: dict[str, dict[str, Any]]


class SaveBoardRequest(AuthRequest):
    board: BoardPayload


class ChatMessage(BaseModel):
    role: str = Field(min_length=1)
    content: str = Field(min_length=1)


class AiBoardRequest(AuthRequest):
    prompt: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


@app.post("/api/auth/register")
async def register(payload: AuthRequest):
    try:
        user_id, board_id = register_user(payload.username, payload.password)
        return {
            "success": True,
            "user_id": user_id,
            "board_id": board_id,
        }
    except Exception as exc:
        message = str(exc).lower()
        if "unique" in message:
            raise HTTPException(status_code=409, detail="Username already exists") from exc
        raise HTTPException(status_code=500, detail="Failed to register user") from exc


@app.post("/api/auth/login")
async def login(payload: AuthRequest):
    user_id = authenticate_user(payload.username, payload.password)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    board_id = get_board_for_user(user_id)
    if board_id is None:
        raise HTTPException(status_code=500, detail="User board not found")

    return {
        "success": True,
        "user_id": user_id,
        "board_id": board_id,
    }


@app.post("/api/board/load")
async def load_user_board(payload: AuthRequest):
    user_id = authenticate_user(payload.username, payload.password)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    board_id = get_board_for_user(user_id)
    if board_id is None:
        raise HTTPException(status_code=500, detail="User board not found")

    return {
        "success": True,
        "board": load_board(board_id),
    }


@app.post("/api/board/save")
async def save_user_board(payload: SaveBoardRequest):
    user_id = authenticate_user(payload.username, payload.password)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    board_id = get_board_for_user(user_id)
    if board_id is None:
        raise HTTPException(status_code=500, detail="User board not found")

    try:
        replace_board(board_id, payload.board.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"success": True}


@app.get("/api/ai/sanity")
async def ai_sanity():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY is not configured")

    try:
        result = openrouter_sanity_check(api_key)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenRouter call failed: {exc}") from exc

    return {
        "success": True,
        "model": "openai/gpt-oss-120b",
        "prompt": "What is 2+2?",
        "response": result,
    }


@app.post("/api/ai/board")
async def ai_board(payload: AiBoardRequest, request: Request, response: Response):
    is_valid_origin, origin_error = _validate_ai_origin(
        origin=request.headers.get("origin"),
        referer=request.headers.get("referer"),
    )
    if not is_valid_origin:
        raise HTTPException(status_code=403, detail=origin_error)

    client_ip = request.client.host if request.client else "unknown"
    is_allowed, limit_error, retry_after = _check_and_consume_ai_rate_limit(client_ip)
    if not is_allowed:
        if retry_after is not None:
            response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(status_code=429, detail=limit_error)

    max_prompt_chars = _get_int_env("AI_MAX_PROMPT_CHARS", 2000, minimum=1)
    max_history_messages = _get_int_env("AI_MAX_HISTORY_MESSAGES", 20, minimum=0)
    max_history_chars = _get_int_env("AI_MAX_HISTORY_CHARS", 8000, minimum=0)
    max_board_context_chars = _get_int_env("AI_MAX_BOARD_CONTEXT_CHARS", 120000, minimum=1)

    if len(payload.prompt) > max_prompt_chars:
        raise HTTPException(status_code=422, detail="Prompt is too large for AI endpoint")

    if len(payload.history) > max_history_messages:
        raise HTTPException(status_code=422, detail="History has too many messages")

    total_history_chars = sum(len(item.content) for item in payload.history)
    if total_history_chars > max_history_chars:
        raise HTTPException(status_code=422, detail="History content is too large")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY is not configured")

    user_id = authenticate_user(payload.username, payload.password)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    board_id = get_board_for_user(user_id)
    if board_id is None:
        raise HTTPException(status_code=500, detail="User board not found")

    current_board = load_board(board_id)
    board_context = json.dumps(current_board)
    if len(board_context) > max_board_context_chars:
        raise HTTPException(status_code=422, detail="Board context is too large for AI endpoint")

    history = [item.model_dump() for item in payload.history]

    try:
        ai_result = openrouter_board_structured_response(
            api_key=api_key,
            prompt=payload.prompt,
            board=current_board,
            history=history,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenRouter call failed: {exc}") from exc

    updated_board = ai_result.get("board")
    board_updated = isinstance(updated_board, dict)

    if board_updated:
        try:
            replace_board(board_id, updated_board)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"AI board update invalid: {exc}") from exc

    final_board = load_board(board_id)

    return {
        "success": True,
        "message": ai_result["message"],
        "board_updated": board_updated,
        "board": final_board,
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")
