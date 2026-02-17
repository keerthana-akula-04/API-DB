import os
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from bson import ObjectId
from database import get_collections

security = HTTPBearer()

ALGORITHM = "HS256"
IDLE_TIMEOUT_MINUTES = 120  # 1 hour


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    SECRET_KEY = os.getenv("SECRET_KEY")

    if not SECRET_KEY:
        raise HTTPException(status_code=500, detail="SECRET_KEY not configured")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        print("Decoded Payload:", payload)

        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        client_id = payload.get("sub")
        if not client_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return {
            "client_id": client_id,
            "username": payload.get("username"),
            "role": payload.get("role")
        }

    except JWTError as e:
        print("JWT ERROR:", str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
