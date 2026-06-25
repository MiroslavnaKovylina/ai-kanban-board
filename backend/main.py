from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import SESSION_COOKIE_NAME, _allowed_ai_origins, _load_project_env  # noqa: F401
from db import get_db_connection
from guards import (  # noqa: F401
    _reset_ai_guards_for_tests,
    _reset_auth_guards_for_tests,
    _reset_board_save_guards_for_tests,
)
from routes.auth import router as auth_router
from routes.board import router as board_router
from routes.ai_board import router as ai_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_project_env()
    get_db_connection()
    yield


app = FastAPI(title="PM MVP Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_allowed_ai_origins()),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(board_router)
app.include_router(ai_router)


@app.get("/api/ping")
async def ping():
    return {"success": True, "message": "pong"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
