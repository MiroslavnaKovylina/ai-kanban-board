from fastapi import HTTPException, Request

from config import SESSION_COOKIE_NAME
from db import get_session_user


def require_session_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_session_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
