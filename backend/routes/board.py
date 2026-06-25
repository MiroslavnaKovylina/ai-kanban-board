from fastapi import APIRouter, Depends, HTTPException, Request

from db import get_board_for_user, load_board, replace_board
from deps import require_session_user
from guards import _check_and_consume_board_save_rate_limit, _client_ip
from models import SaveBoardRequest

router = APIRouter()


@router.post("/api/board/load")
async def load_user_board(current_user=Depends(require_session_user)):
    user_id = int(current_user["id"])
    board_id = get_board_for_user(user_id)
    if board_id is None:
        raise HTTPException(status_code=500, detail="User board not found")

    return {"success": True, "board": load_board(board_id)}


@router.post("/api/board/save")
async def save_user_board(
    payload: SaveBoardRequest,
    request: Request,
    current_user=Depends(require_session_user),
):
    client_ip = _client_ip(request)
    is_allowed, limit_error, retry_after = _check_and_consume_board_save_rate_limit(client_ip)
    if not is_allowed:
        headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
        raise HTTPException(status_code=429, detail=limit_error, headers=headers)

    user_id = int(current_user["id"])
    board_id = get_board_for_user(user_id)
    if board_id is None:
        raise HTTPException(status_code=500, detail="User board not found")

    try:
        replace_board(board_id, payload.board.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"success": True}
