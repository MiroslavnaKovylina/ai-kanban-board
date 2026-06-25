import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ai import openrouter_board_structured_response, openrouter_sanity_check
from config import _get_int_env
from db import get_board_for_user, load_board, replace_board
from deps import require_session_user
from guards import _check_and_consume_ai_rate_limit, _client_ip, _validate_ai_origin
from models import AiBoardRequest

router = APIRouter()


@router.get("/api/ai/sanity")
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


@router.post("/api/ai/board")
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

    client_ip = _client_ip(request)
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
