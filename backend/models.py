from typing import Any

from pydantic import BaseModel, Field, field_validator


class AuthRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("Username is required")
        return username


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
