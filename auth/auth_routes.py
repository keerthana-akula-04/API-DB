import os
import uuid
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from jose import jwt, JWTError

from database import get_collections
from auth.auth_models import LoginRequest, RefreshRequest
from auth.auth_service import create_access_token, create_refresh_token

# SQLite imports
from sqlite_db import SessionLocal
from auth.sqlite_session_model import Session as SQLiteSession


router = APIRouter(prefix="/auth", tags=["Authentication"])

IDLE_TIMEOUT_MINUTES = 120


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

    # ✅ Store Session in SQLite
    db_sqlite = SessionLocal()

    new_session = SQLiteSession(
        session_id=session_id,
        client_id=str(user["_id"]),
        refresh_jti=decoded_refresh["jti"],
        refresh_token=refresh_token,
        device_info="web",
        issued_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=15),
        last_activity=datetime.utcnow(),
        revoked=False
    )

    db_sqlite.add(new_session)
    db_sqlite.commit()
    db_sqlite.close()

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
        client_id = payload.get("sub")

        # ✅ Get Session from SQLite
        db_sqlite = SessionLocal()

        session = db_sqlite.query(SQLiteSession).filter(
            SQLiteSession.client_id == client_id,
            SQLiteSession.refresh_jti == refresh_jti,
            SQLiteSession.revoked == False
        ).first()

        if not session:
            db_sqlite.close()
            raise HTTPException(status_code=401, detail="Session not found")

        # Idle Timeout Check
        if datetime.utcnow() - session.last_activity > timedelta(minutes=IDLE_TIMEOUT_MINUTES):
            session.revoked = True
            db_sqlite.commit()
            db_sqlite.close()
            raise HTTPException(status_code=401, detail="Session expired due to inactivity")

        # Update Last Activity
        session.last_activity = datetime.utcnow()
        db_sqlite.commit()
        db_sqlite.close()

        # Fetch full user details from Mongo
        user = await cols["clients"].find_one({"_id": ObjectId(client_id)})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_access_token = create_access_token({
            "sub": str(client_id),
            "username": user["client_name"],
            "role": user["role"]
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

    try:
        payload = jwt.decode(
            data.refresh_token,
            os.getenv("SECRET_KEY"),
            algorithms=["HS256"]
        )

        db_sqlite = SessionLocal()

        session = db_sqlite.query(SQLiteSession).filter(
            SQLiteSession.refresh_jti == payload.get("jti")
        ).first()

        if session:
            session.revoked = True
            db_sqlite.commit()

        db_sqlite.close()

        return {"message": "Logged out successfully"}

    except:
        raise HTTPException(status_code=401, detail="Invalid token")
