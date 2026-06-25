from fastapi import Response

from config import SESSION_COOKIE_NAME, _session_cookie_secure, _session_ttl_days


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
