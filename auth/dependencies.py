import os
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from bson import ObjectId
from database import get_collections

security = HTTPBearer()

ALGORITHM = "HS256"
IDLE_TIMEOUT_MINUTES = 60  # 1 hour


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    # 🔥 Always fetch SECRET_KEY dynamically (avoids None issue)
    SECRET_KEY = os.getenv("SECRET_KEY")

    if not SECRET_KEY:
        raise HTTPException(status_code=500, detail="SECRET_KEY not configured")

    try:
        # 🔥 Decode token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Debug (you can remove later)
        print("Decoded Payload:", payload)

        # 🔥 Ensure it's an access token
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        client_id = payload.get("sub")
        if not client_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        client_id = ObjectId(client_id)

        cols = get_collections()

        # 🔥 Check active session
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

        print("Logged in user role:", payload.get("role"))

        return {
            "client_id": str(client_id),
            "username": payload.get("username"),
            "role": payload.get("role")
        }

    except JWTError as e:
        print("JWT ERROR:", str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
