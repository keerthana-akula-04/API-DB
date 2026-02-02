import os
import time
import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from dotenv import load_dotenv

from database import get_collections
from otp_service import generate_otp, send_otp_email
from auth.auth_models import LoginRequest, OTPVerifyRequest

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ================= CONFIG =================
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

if not SECRET_KEY:
    raise Exception("❌ JWT_SECRET_KEY not set in environment variables")

security = HTTPBearer()

otp_store = {}
verified_users = {}


# ================= HELPERS =================
async def cleanup_otp(username: str, delay: int):
    await asyncio.sleep(delay)
    otp_store.pop(username, None)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ================= LOGIN =================
@router.post("/login")
async def login(data: LoginRequest, background_tasks: BackgroundTasks):
    cols = get_collections()
    users_auth_col = cols["users_auth_col"]

    user = await users_auth_col.find_one({"username": data.username})

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.get("password") != data.password:
        raise HTTPException(status_code=401, detail="Incorrect password")

    if user.get("role") != data.required_role:
        raise HTTPException(status_code=403, detail="Unauthorized role")

    otp = generate_otp()

    otp_store[data.username] = {
        "otp": otp,
        "expires_at": time.time() + 120
    }

    # ✅ Brevo email sending
    send_otp_email(otp, data.required_role)

    background_tasks.add_task(cleanup_otp, data.username, 120)

    return {
        "success": True,
        "message": "OTP sent successfully"
    }


# ================= VERIFY OTP =================
@router.post("/verify-otp")
async def verify_otp(data: OTPVerifyRequest):
    record = otp_store.get(data.username)

    if not record:
        raise HTTPException(status_code=400, detail="OTP expired or not found")

    if time.time() > record["expires_at"]:
        otp_store.pop(data.username, None)
        raise HTTPException(status_code=400, detail="OTP expired")

    if record["otp"] != str(data.otp):
        raise HTTPException(status_code=401, detail="Invalid OTP")

    # allow token fetch for 5 mins
    verified_users[data.username] = time.time() + 300

    otp_store.pop(data.username, None)

    return {
        "success": True,
        "message": "OTP verified successfully"
    }


# ================= GET JWT TOKEN =================
@router.get("/token")
async def get_token(username: str):
    expiry = verified_users.get(username)

    if not expiry or time.time() > expiry:
        raise HTTPException(
            status_code=401,
            detail="OTP verification required"
        )

    cols = get_collections()
    users_auth_col = cols["users_auth_col"]

    user = await users_auth_col.find_one(
        {"username": username},
        {"_id": 0, "password": 0}
    )

    token = create_access_token({
        "sub": user["username"],
        "role": user.get("role")
    })

    verified_users.pop(username, None)

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer"
    }


# ================= PROTECTED ROUTE =================
@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return {
        "success": True,
        "user": current_user
    }
