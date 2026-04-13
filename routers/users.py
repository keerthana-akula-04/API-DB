from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from database import get_collections
from auth.dependencies import get_current_user
from utils.security import hash_password 

router = APIRouter(prefix="/users", tags=["Users"])


class UserRegisterRequest(BaseModel):
    client_name: str | None = Field(default=None, alias="Client Name")
    user_name: str = Field(..., alias="User Name")
    email_id: EmailStr = Field(..., alias="Email")
    password: str

    class Config:
        populate_by_name = True  


@router.post("/register")
async def register_user(
    data: UserRegisterRequest,
    user=Depends(get_current_user)
):
    cols = get_collections()
    clients_collection = cols["clients"]

    role = user.get("role")

    if role == "super_admin":
        if not data.client_name:
            raise HTTPException(status_code=400, detail="clientName is required")
        client_name = data.client_name

    elif role == "admin":
        client_name = user.get("client_name")

        if not client_name:
            admin_data = await clients_collection.find_one(
                {"email_id": user.get("email_id")}
            )
            if not admin_data:
                raise HTTPException(status_code=404, detail="Admin not found")
            client_name = admin_data.get("client_name")

    else:
        raise HTTPException(status_code=403, detail="Access denied")

    existing_user = await clients_collection.find_one({"email_id": data.email_id})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

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