from fastapi import Header, HTTPException
from supabase_auth.errors import AuthError

import config
import db


def get_current_user(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ")

    try:
        response = db.get_supabase().auth.get_user(token)
    except AuthError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if response is None or response.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = response.user
    allowed_emails = {email.lower() for email in config.ALLOWED_EMAILS}
    if (user.email or "").lower() not in allowed_emails:
        raise HTTPException(status_code=403, detail="This account is not authorized")

    return user.id
