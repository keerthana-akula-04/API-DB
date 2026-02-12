import os
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from bson import ObjectId
from database import get_collections

security = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

IDLE_TIMEOUT_MINUTES = 60  # 👈 1 hour


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")

        client_id = ObjectId(payload.get("sub"))

        cols = get_collections()

        session = await cols["sessions_col"].find_one(
            {
                "client_id": client_id,
                "revoked": False
            }
        )

        if not session:
            raise HTTPException(status_code=401, detail="Session not found")

        # 🔥 Idle Timeout Check
        if datetime.utcnow() - session["last_activity"] > timedelta(minutes=IDLE_TIMEOUT_MINUTES):
            await cols["sessions_col"].update_one(
                {"_id": session["_id"]},
                {"$set": {"revoked": True}}
            )
            raise HTTPException(status_code=401, detail="Session expired due to inactivity")

        # 🔥 Update Last Activity
        await cols["sessions_col"].update_one(
            {"_id": session["_id"]},
            {"$set": {"last_activity": datetime.utcnow()}}
        )

        return {
            "client_id": payload.get("sub"),
            "username": payload.get("username"),
            "role": payload.get("role")
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
