from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime

from database import get_collections
from auth.dependencies import get_current_user
from routers.admins import hash_password   # reuse existing function

router = APIRouter(prefix="/users", tags=["Users"])


class UserRegisterRequest(BaseModel):
    client_name: str | None = None
    user_name: str
    email_id: EmailStr
    password: str


@router.post("/register")
async def register_user(
    data: UserRegisterRequest,
    user=Depends(get_current_user)
):
    cols = get_collections()
    clients_collection = cols["clients"]

    role = user.get("role")

    # 🔐 Role-based logic
    if role == "super_admin":
        if not data.client_name:
            raise HTTPException(status_code=400, detail="client_name is required")
        client_name = data.client_name

    elif role == "admin":
        client_name = user.get("client_name")

    else:
        raise HTTPException(status_code=403, detail="Access denied")

    # ❌ Duplicate check
    existing_user = await clients_collection.find_one({"email_id": data.email_id})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # ✅ Create user
    new_user = {
        "client_name": client_name,
        "user_name": data.user_name,
        "email_id": data.email_id,
        "password": hash_password(data.password),
        "role": "user",
        "status": "Active",
        "created_at": datetime.utcnow()
    }

    result = await clients_collection.insert_one(new_user)

    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id),
        "client_name": client_name
    }