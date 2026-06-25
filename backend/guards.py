import os
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import urlparse

from fastapi import Request

from config import _get_bool_env, _get_int_env, _allowed_ai_origins

_ai_guard_lock = Lock()
_ai_minute_windows: dict[str, deque[float]] = defaultdict(deque)
_ai_daily_usage: dict[str, tuple[str, int]] = {}

_auth_guard_lock = Lock()
_auth_attempt_windows: dict[str, deque[float]] = defaultdict(deque)

_board_save_guard_lock = Lock()
_board_save_windows: dict[str, deque[float]] = defaultdict(deque)

_MAX_TRACKED_KEYS = 10_000


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _normalize_origin(header_value: str) -> str:
    parsed = urlparse(header_value)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return header_value.strip().rstrip("/")


def _validate_ai_origin(origin: str | None, referer: str | None) -> tuple[bool, str]:
    if not origin and not referer:
        # Allow headerless requests only when explicitly enabled (e.g. for API clients
        # in development or testing). In production this should remain False.
        if _get_bool_env("AI_ALLOW_HEADERLESS", False):
            return True, ""
        return False, "Origin or Referer required for AI endpoint"

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
        for tracked_ip, tracked_window in list(_ai_minute_windows.items()):
            while tracked_window and tracked_window[0] <= minute_cutoff:
                tracked_window.popleft()
            if not tracked_window:
                del _ai_minute_windows[tracked_ip]

        for tracked_ip, (usage_day, _) in list(_ai_daily_usage.items()):
            if usage_day != today:
                del _ai_daily_usage[tracked_ip]

        window = _ai_minute_windows[ip_address]
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
        # Bound dict size to prevent unbounded memory growth from abandoned attack scans.
        if len(_auth_attempt_windows) > _MAX_TRACKED_KEYS:
            _auth_attempt_windows.clear()

        for tracked_key, tracked_window in list(_auth_attempt_windows.items()):
            while tracked_window and tracked_window[0] <= cutoff:
                tracked_window.popleft()
            if not tracked_window:
                del _auth_attempt_windows[tracked_key]

        for key in keys:
            window = _auth_attempt_windows[key]
            if len(window) >= limit:
                retry_after = max(1, int(window[0] + window_seconds - now))
                return False, "Too many authentication attempts. Please retry later.", retry_after

        for key in keys:
            _auth_attempt_windows[key].append(now)

    return True, "", None


def _check_and_consume_board_save_rate_limit(ip_address: str) -> tuple[bool, str, int | None]:
    per_minute_limit = _get_int_env("BOARD_SAVE_RATE_LIMIT_PER_MINUTE", 120, minimum=1)

    now = time.time()
    minute_cutoff = now - 60

    with _board_save_guard_lock:
        if len(_board_save_windows) > _MAX_TRACKED_KEYS:
            _board_save_windows.clear()

        for tracked_ip, tracked_window in list(_board_save_windows.items()):
            while tracked_window and tracked_window[0] <= minute_cutoff:
                tracked_window.popleft()
            if not tracked_window:
                del _board_save_windows[tracked_ip]

        window = _board_save_windows[ip_address]
        if len(window) >= per_minute_limit:
            retry_after = max(1, int(window[0] + 60 - now))
            return False, "Too many board save requests. Please slow down.", retry_after

        window.append(now)

    return True, "", None


def _reset_ai_guards_for_tests() -> None:
    with _ai_guard_lock:
        _ai_minute_windows.clear()
        _ai_daily_usage.clear()


def _reset_auth_guards_for_tests() -> None:
    with _auth_guard_lock:
        _auth_attempt_windows.clear()


def _reset_board_save_guards_for_tests() -> None:
    with _board_save_guard_lock:
        _board_save_windows.clear()
