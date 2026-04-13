from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
import uuid

from database import get_collections
from auth.dependencies import get_current_user
from utils.security import hash_password

router = APIRouter(prefix="/admins", tags=["Admins"])

def require_super_admin(user=Depends(get_current_user)):
    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return user

class AdminRegisterRequest(BaseModel):
    client_name: str = Field(..., alias="clientName")
    email_id: EmailStr = Field(..., alias="email")
    password: str

    class Config:
        populate_by_name = True

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

@router.post("/register")
async def register_admin(
    data: AdminRegisterRequest,
    user=Depends(require_super_admin)
):

    cols = get_collections()
    clients_collection = cols["clients"]

    existing_user = await clients_collection.find_one({"email_id": data.email_id})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_admin = {
        "client_code": f"C_{str(uuid.uuid4())[:6]}",  
        "client_name": data.client_name,
        "email_id": data.email_id,
        "password": hash_password(data.password),

        "role": "admin",
        "status": "Active",

        "admin_name": data.client_name,   
        "admin_contact_number": "9999999999",  
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await clients_collection.insert_one(new_admin)

    return {
        "status": "success",
        "message": "Admin registered successfully",
        "data": {
            "admin_id": str(result.inserted_id),
            "client_name": data.client_name,
            "email": data.email_id
        }
    } 