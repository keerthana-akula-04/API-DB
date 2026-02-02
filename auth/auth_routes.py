import os
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from jose import jwt
from dotenv import load_dotenv

from database import get_collections
from otp_service import generate_otp, send_otp_email
from pydantic import BaseModel

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ================= CONFIG =================
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 10

if not SECRET_KEY:
    raise Exception("JWT_SECRET_KEY missing")


# ================= Schemas =================
class LoginRequest(BaseModel):
    username: str
    password: str


class OTPVerifyRequest(BaseModel):
    username: str
    otp: str


# ================= In-memory stores =================
otp_store = {}
verified_users = {}


# ================= LOGIN =================
@router.post("/login")
async def login(data: LoginRequest):
    cols = get_collections()
    users_col = cols["users_auth_col"]

    user = await users_col.find_one({"username": data.username.lower()})

    if not user or user["password"] != data.password:
        raise HTTPException(401, "Invalid credentials")

    otp = generate_otp()

    otp_store[data.username] = {
        "otp": otp,
        "expires": time.time() + 120
    }

    # always send to your fixed email
    send_otp_email(otp, user["role"])

    return {"message": "OTP sent successfully"}


# ================= VERIFY OTP =================
@router.post("/verify-otp")
async def verify(data: OTPVerifyRequest):
    record = otp_store.get(data.username)

    if not record:
        raise HTTPException(401, "OTP not found")

    if time.time() > record["expires"]:
        raise HTTPException(401, "OTP expired")

    if record["otp"] != data.otp:
        raise HTTPException(401, "Invalid OTP")

    verified_users[data.username] = True
    otp_store.pop(data.username)

    return {"message": "OTP verified successfully"}


# ================= SUCCESS → ISSUE JWT =================
@router.get("/success")
async def success(username: str):
    if not verified_users.get(username):
        raise HTTPException(401, "OTP not verified")

    cols = get_collections()
    users_col = cols["users_auth_col"]

    user = await users_col.find_one({"username": username})

    token = jwt.encode(
        {
            "username": username,
            "role": user["role"],
            "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    verified_users.pop(username)

    return {
        "status": "success",
        "token": token,
        "role": user["role"],
        "username": username
    }
