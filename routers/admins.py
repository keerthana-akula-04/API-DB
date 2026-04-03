from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime
from passlib.context import CryptContext

from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/admins", tags=["Admins"])


# 🔐 Role Check (Admin / Super Admin)
def require_super_admin(user=Depends(get_current_user)):
    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return user


# 🔒 Password Hashing Setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


# 📥 Request Model for Admin Registration
class AdminRegisterRequest(BaseModel):
    client_name: str
    email_id: EmailStr
    password: str


# 📋 Get All Admins / Users / Pilots
@router.get("/")
async def get_admins(user=Depends(require_super_admin)):

    cols = get_collections()

    users = await cols["clients"].find(
        {
            "role": {"$in": ["admin", "user", "pilot"]},
            "status": "Active"
        },
        {
            "password": 0
        }
    ).to_list(100)

    for u in users:
        u["_id"] = str(u["_id"])

    return users


# 🚀 Admin Registration API
@router.post("/register")
async def register_admin(
    data: AdminRegisterRequest,
    user=Depends(require_super_admin)   # 🔐 Only admin/super_admin can create
):

    cols = get_collections()
    clients_collection = cols["clients"]

    # ❌ Check if email already exists
    existing_user = await clients_collection.find_one({"email_id": data.email_id})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # ✅ Create new admin
    new_admin = {
        "client_name": data.client_name,
        "email_id": data.email_id,
        "password": hash_password(data.password),
        "role": "admin",
        "status": "Active",
        "created_at": datetime.utcnow()
    }

    result = await clients_collection.insert_one(new_admin)

    return {
        "message": "Admin registered successfully",
        "admin_id": str(result.inserted_id)
    }