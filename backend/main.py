from typing import Any
from collections import defaultdict, deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import time
from threading import Lock
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles

from ai import openrouter_board_structured_response, openrouter_sanity_check

from db import (
    authenticate_user,
    create_session,
    delete_session,
    get_board_for_user,
    get_db_connection,
    get_session_user,
    load_board,
    register_user,
    replace_board,
)

app = FastAPI(title="PM MVP Backend")
SESSION_COOKIE_NAME = "kanban_session"

_ai_guard_lock = Lock()
_ai_minute_windows: dict[str, deque[float]] = defaultdict(deque)
_ai_daily_usage: dict[str, tuple[str, int]] = {}
_auth_guard_lock = Lock()
_auth_attempt_windows: dict[str, deque[float]] = defaultdict(deque)


def _get_int_env(name: str, default: int, minimum: int = 0) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return max(value, minimum)


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _session_ttl_days() -> int:
    return _get_int_env("SESSION_TTL_DAYS", 7, minimum=1)


def _is_local_development() -> bool:
    environment = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "local")).strip().lower()
    return environment in {"local", "dev", "development", "test"}


def _session_cookie_secure() -> bool:
    raw_value = os.getenv("SESSION_COOKIE_SECURE")
    if raw_value is not None:
        return _get_bool_env("SESSION_COOKIE_SECURE", False)
    # Local Docker runs on HTTP. Production must set SESSION_COOKIE_SECURE=true.
    return not _is_local_development()


def _set_session_cookie(response: Response, token: str) -> None:
    ttl_days = _session_ttl_days()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=_session_cookie_secure(),
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=_session_cookie_secure(),
        samesite="lax",
        path="/",
    )


def require_session_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_session_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


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


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_and_consume_auth_rate_limit(
    request: Request,
    action: str,
    username: str,
) -> tuple[bool, str, int | None]:
    limit = _get_int_env("AUTH_RATE_LIMIT_ATTEMPTS", 10, minimum=1)
    window_seconds = _get_int_env("AUTH_RATE_LIMIT_WINDOW_SECONDS", 300, minimum=1)

    now = time.time()
    cutoff = now - window_seconds
    normalized_username = username.strip().lower()
    keys = [
        f"{action}:ip:{_client_ip(request)}",
        f"{action}:user:{normalized_username}",
    ]

    with _auth_guard_lock:
        for key in keys:
            window = _auth_attempt_windows[key]
            while window and window[0] <= cutoff:
                window.popleft()

            if len(window) >= limit:
                retry_after = max(1, int(window[0] + window_seconds - now))
                return False, "Too many authentication attempts. Please retry later.", retry_after

        for key in keys:
            _auth_attempt_windows[key].append(now)

    return True, "", None


def _reset_ai_guards_for_tests() -> None:
    with _ai_guard_lock:
        _ai_minute_windows.clear()
        _ai_daily_usage.clear()


def _reset_auth_guards_for_tests() -> None:
    with _auth_guard_lock:
        _auth_attempt_windows.clear()

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


class SaveBoardRequest(BaseModel):
    board: BoardPayload


class ChatMessage(BaseModel):
    role: str = Field(min_length=1)
    content: str = Field(min_length=1)


class AiBoardRequest(BaseModel):
    prompt: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


@app.post("/api/auth/register")
async def register(payload: AuthRequest, request: Request, response: Response):
    is_allowed, limit_error, retry_after = _check_and_consume_auth_rate_limit(
        request,
        "register",
        payload.username,
    )
    if not is_allowed:
        headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
        raise HTTPException(status_code=429, detail=limit_error, headers=headers)

    try:
        user_id, board_id = register_user(payload.username, payload.password)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Username already exists") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to register user") from exc

    token, _ = create_session(user_id, ttl_days=_session_ttl_days())
    _set_session_cookie(response, token)

    return {
        "success": True,
        "user_id": user_id,
        "board_id": board_id,
    }


@app.post("/api/auth/login")
async def login(payload: AuthRequest, request: Request, response: Response):
    is_allowed, limit_error, retry_after = _check_and_consume_auth_rate_limit(
        request,
        "login",
        payload.username,
    )
    if not is_allowed:
        headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
        raise HTTPException(status_code=429, detail=limit_error, headers=headers)

    user_id = authenticate_user(payload.username, payload.password)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    board_id = get_board_for_user(user_id)
    if board_id is None:
        raise HTTPException(status_code=500, detail="User board not found")

    token, _ = create_session(user_id, ttl_days=_session_ttl_days())
    _set_session_cookie(response, token)

    return {
        "success": True,
        "user_id": user_id,
        "board_id": board_id,
    }


@app.get("/api/auth/me")
async def auth_me(current_user=Depends(require_session_user)):
    board_id = get_board_for_user(int(current_user["id"]))
    if board_id is None:
        raise HTTPException(status_code=500, detail="User board not found")

    return {
        "success": True,
        "user_id": int(current_user["id"]),
        "username": current_user["username"],
        "board_id": board_id,
    }


@app.post("/api/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    delete_session(token)
    _clear_session_cookie(response)
    return {"success": True}


@app.post("/api/board/load")
async def load_user_board(current_user=Depends(require_session_user)):
    user_id = int(current_user["id"])
    board_id = get_board_for_user(user_id)
    if board_id is None:
        raise HTTPException(status_code=500, detail="User board not found")

    return {
        "success": True,
        "board": load_board(board_id),
    }


@app.post("/api/board/save")
async def save_user_board(payload: SaveBoardRequest, current_user=Depends(require_session_user)):
    user_id = int(current_user["id"])
    board_id = get_board_for_user(user_id)
    if board_id is None:
        raise HTTPException(status_code=500, detail="User board not found")

    try:
        replace_board(board_id, payload.board.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"success": True}


@app.get("/api/ai/sanity")
async def ai_sanity(current_user=Depends(require_session_user)):
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
async def ai_board(
    payload: AiBoardRequest,
    request: Request,
    response: Response,
    current_user=Depends(require_session_user),
):
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

    user_id = int(current_user["id"])
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
