from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from database import get_collections
from auth.dependencies import get_current_user
from utils.security import hash_password

router = APIRouter(prefix="/admin", tags=["Registrations"])

class AdminRegisterRequest(BaseModel):
    client_name: str = Field(..., alias="Client Name")
    industry_name: str = Field(..., alias="Industry Name")
    email_id: EmailStr = Field(..., alias="Email")
    password: str = Field(..., alias="Password")

    class Config:
        populate_by_name = True

@router.get("/data")
async def get_admin_form_data(user=Depends(get_current_user)):

    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    cols = get_collections()
    clients_collection = cols["clients"]
    projects_collection = cols["projects_client"]

    clients = await clients_collection.find().to_list(None)
    projects = await projects_collection.find().to_list(None)

    # Group clients by name
    client_map = {}

    for c in clients:
        name = c["client_name"]

        if name not in client_map:
            client_map[name] = {"client_ids": []}

        client_map[name]["client_ids"].append(c["_id"])

    result = []

    for client_name, data in client_map.items():

        industries = []

        for p in projects:
            if p["client_id"] in data["client_ids"]:
                industries.append(p["project_name"])

        result.append({
            "client_name": client_name,
            "industries": list(set(industries))
        })

    return {
        "status": "success",
        "data": result
    }

@router.post("/register")
async def register_admin(
    data: AdminRegisterRequest,
    user=Depends(get_current_user)
):

    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    cols = get_collections()
    clients_collection = cols["clients"]
    projects_collection = cols["projects_client"]

    # 1. VALIDATE CLIENT NAME
    existing_client = await clients_collection.find_one({
        "client_name": data.client_name
    })

    if not existing_client:
        raise HTTPException(400, "Invalid client name")

    client_code = existing_client["client_code"]

    # 2. USER LIMIT CHECK (MAX 10 USERS)
    user_count = await clients_collection.count_documents({
        "client_code": client_code
    })

    if user_count >= 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 users allowed for this client"
        )

    # 3. EMAIL UNIQUENESS CHECK
    existing_user = await clients_collection.find_one({
        "email_id": data.email_id
    })

    if existing_user:
        raise HTTPException(400, "Email already registered")

    # 4. VALIDATE INDUSTRY (NO STORAGE)
    client_records = await clients_collection.find({
        "client_name": data.client_name
    }).to_list(None)

    client_ids = [c["_id"] for c in client_records]

    valid_project = await projects_collection.find_one({
        "project_name": data.industry_name,
        "client_id": {"$in": client_ids}
    })

    if not valid_project:
        raise HTTPException(
            status_code=400,
            detail="Invalid industry for selected client"
        )

    # 5. CREATE ADMIN (NO NEW FIELDS ADDED)
    new_admin = {
        "client_code": client_code,
        "client_name": data.client_name,

        "email_id": data.email_id,
        "password":  data.password,

        "role": "admin",
        "status": "Active",

        "admin_name": data.client_name,
        "admin_contact_number": "",

        "logo_path": existing_client.get("logo_path", ""),

        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await clients_collection.insert_one(new_admin)

    return {
        "status": "success",
        "message": "Admin registered successfully",
        "data": {
            "adminId": str(result.inserted_id),
            "clientName": data.client_name,
            "industryName": data.industry_name,
            "email": data.email_id
        }
    }