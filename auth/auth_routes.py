import time
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel

from database import get_collections
from otp_service import generate_otp, send_otp_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ================= CONFIG =================
# ✅ AUTO generate secret (NO ENV needed)
SECRET_KEY = secrets.token_hex(32)

ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 10

print("✅ JWT Secret auto-generated")


# ================= Schemas =================
class LoginRequest(BaseModel):
    username: str
    password: str


class OTPVerifyRequest(BaseModel):
    username: str
    otp: str


# ================= Memory Stores =================
otp_store = {}
verified_users = {}   # username -> expiry


# ================= LOGIN =================
@router.post("/login")
async def login(data: LoginRequest):
    username = data.username.lower()

    cols = get_collections()
    users_col = cols["users_auth_col"]

    user = await users_col.find_one({"username": username})

    if not user or user["password"] != data.password:
        raise HTTPException(401, "Invalid credentials")

    otp = generate_otp()

    otp_store[username] = {
        "otp": otp,
        "expires": time.time() + 120
    }

    send_otp_email(otp, user["role"])

    return {"message": "OTP sent successfully"}


# ================= VERIFY OTP =================
@router.post("/verify-otp")
async def verify(data: OTPVerifyRequest):
    username = data.username.lower()

    record = otp_store.get(username)

    if not record:
        raise HTTPException(401, "OTP not found")

    if time.time() > record["expires"]:
        otp_store.pop(username, None)
        raise HTTPException(401, "OTP expired")

    if record["otp"] != data.otp:
        raise HTTPException(401, "Invalid OTP")

    verified_users[username] = time.time() + 300

    otp_store.pop(username, None)

    return {"message": "OTP verified successfully"}


# ================= SUCCESS → RETURN JWT =================
@router.get("/success")
async def success(username: str):
    username = username.lower()

    expiry = verified_users.get(username)

    if not expiry or time.time() > expiry:
        raise HTTPException(401, "OTP not verified")

    cols = get_collections()
    users_col = cols["users_auth_col"]

    user = await users_col.find_one({"username": username})

    token = jwt.encode(
        {
            "sub": username,
            "role": user["role"],
            "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    verified_users.pop(username, None)

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "username": username,
        "role": user["role"]
    }
