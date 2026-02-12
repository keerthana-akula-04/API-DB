import os
import uuid
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from jose import jwt, JWTError

from database import get_collections
from auth.auth_models import LoginRequest, RefreshRequest
from auth.auth_service import create_access_token, create_refresh_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ================= LOGIN =================
@router.post("/login")
async def login(data: LoginRequest):

    cols = get_collections()

    user = await cols["clients"].find_one({
        "email_id": data.email,
        "status": "Active"
    })

    if not user or user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({
        "sub": str(user["_id"]),
        "username": user["client_name"],
        "role": user["role"]
    })

    refresh_token = create_refresh_token({
        "sub": str(user["_id"])
    })

    decoded_refresh = jwt.decode(
        refresh_token,
        os.getenv("SECRET_KEY"),
        algorithms=["HS256"]
    )

    session_id = str(uuid.uuid4())

    await cols["sessions_col"].insert_one({
        "session_id": session_id,
        "client_id": user["_id"],
        "refresh_jti": decoded_refresh["jti"],
        "refresh_token": refresh_token,
        "device_info": "web",
        "issued_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=15),
        "revoked": False
    })

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 900
    }


# ================= REFRESH =================
@router.post("/refresh")
async def refresh(data: RefreshRequest):

    cols = get_collections()

    try:
        payload = jwt.decode(
            data.refresh_token,
            os.getenv("SECRET_KEY"),
            algorithms=["HS256"]
        )

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        refresh_jti = payload.get("jti")
        client_id = ObjectId(payload.get("sub"))

        session = await cols["sessions_col"].find_one({
            "client_id": client_id,
            "refresh_jti": refresh_jti,
            "revoked": False
        })

        if not session:
            raise HTTPException(status_code=401, detail="Session not found")

        if datetime.utcnow() > session["expires_at"]:
            raise HTTPException(status_code=401, detail="Session expired")

        new_access_token = create_access_token({
            "sub": str(client_id)
        })

        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


# ================= LOGOUT =================
@router.post("/logout")
async def logout(data: RefreshRequest):

    cols = get_collections()

    try:
        payload = jwt.decode(
            data.refresh_token,
            os.getenv("SECRET_KEY"),
            algorithms=["HS256"]
        )

        await cols["sessions_col"].update_one(
            {"refresh_jti": payload.get("jti")},
            {"$set": {"revoked": True}}
        )

        return {"message": "Logged out successfully"}

    except:
        raise HTTPException(status_code=401, detail="Invalid token")
