from typing import Any
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles

from ai import openrouter_sanity_check

from db import (
    authenticate_user,
    get_board_for_user,
    get_db_connection,
    load_board,
    register_user,
    replace_board,
)

app = FastAPI(title="PM MVP Backend")

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


@app.on_event("startup")
def startup() -> None:
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


app.mount("/", StaticFiles(directory="static", html=True), name="static")
