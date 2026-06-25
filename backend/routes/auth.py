import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from config import SESSION_COOKIE_NAME, _session_ttl_days
from cookies import _clear_session_cookie, _set_session_cookie
from db import authenticate_user, create_session, delete_session, get_board_for_user, register_user
from deps import require_session_user
from guards import _check_and_consume_auth_rate_limit
from models import AuthRequest

router = APIRouter()


@router.post("/api/auth/register")
async def register(payload: AuthRequest, request: Request, response: Response):
    is_allowed, limit_error, retry_after = _check_and_consume_auth_rate_limit(
        request, "register", payload.username,
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

    return {"success": True, "user_id": user_id, "board_id": board_id}


@router.post("/api/auth/login")
async def login(payload: AuthRequest, request: Request, response: Response):
    is_allowed, limit_error, retry_after = _check_and_consume_auth_rate_limit(
        request, "login", payload.username,
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

    return {"success": True, "user_id": user_id, "board_id": board_id}


@router.get("/api/auth/me")
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


@router.post("/api/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    delete_session(token)
    _clear_session_cookie(response)
    return {"success": True}
