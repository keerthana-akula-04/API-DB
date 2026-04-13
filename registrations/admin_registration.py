from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
import uuid

from database import get_collections
from auth.dependencies import get_current_user
from utils.security import hash_password

router = APIRouter(prefix="/register/admin", tags=["Registration"])


# -------------------------------
# 🔹 REQUEST MODEL (Frontend Mapping)
# -------------------------------
class AdminRegisterRequest(BaseModel):
    client_name: str = Field(..., alias="Client Name")
    contact_number: str = Field(..., alias="Contact Number")
    email_id: EmailStr = Field(..., alias="Email")
    password: str

    class Config:
        populate_by_name = True


# -------------------------------
# 🔹 ADMIN REGISTRATION API
# -------------------------------
@router.post("/")
async def register_admin(
    data: AdminRegisterRequest,
    user=Depends(get_current_user)
):

    # 🔐 Role check (only admin / super_admin can create)
    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    cols = get_collections()
    clients_collection = cols["clients"]

    # -------------------------------
    # ❌ Check duplicate email
    # -------------------------------
    existing_user = await clients_collection.find_one({
        "email_id": data.email_id
    })

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # -------------------------------
    # 🔢 Generate client_code
    # -------------------------------
    client_code = f"C_{str(uuid.uuid4())[:6]}"

    # -------------------------------
    # 🧱 Build Admin Document
    # -------------------------------
    new_admin = {
        "client_code": client_code,
        "client_name": data.client_name,
        "email_id": data.email_id,
        "password": hash_password(data.password),

        "role": "admin",
        "status": "Active",

        # 🔥 From frontend
        "admin_name": data.client_name,
        "admin_contact_number": data.contact_number,

        "logo_path": "",  # optional

        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    # -------------------------------
    # 💾 Insert into DB
    # -------------------------------
    result = await clients_collection.insert_one(new_admin)

    # -------------------------------
    # ✅ Response
    # -------------------------------
    return {
        "status": "success",
        "message": "Admin registered successfully",
        "data": {
            "adminId": str(result.inserted_id),
            "clientCode": client_code,
            "clientName": data.client_name,
            "email": data.email_id,
            "contactNumber": data.contact_number
        }
    }