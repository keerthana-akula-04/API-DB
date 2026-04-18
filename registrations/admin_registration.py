from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["Registrations"])


# =========================================================
# 📦 SCHEMA
# =========================================================
class AdminRegisterRequest(BaseModel):
    client_name: str = Field(alias="Client Name")
    industry_name: str = Field(alias="Industry Name")
    name: str = Field(alias="Name")
    email_id: EmailStr = Field(alias="Email")
    password: str = Field(alias="Password")

    class Config:
        populate_by_name = True


# =========================================================
# 🚀 POST API → REGISTER ADMIN (WITH DEBUG LOGS)
# =========================================================
@router.post("/register")
async def register_admin(
    request: Request,   # 👈 to capture raw body
    data: AdminRegisterRequest,
    user=Depends(get_current_user)
):

    # ================= DEBUG START =================
    print("\n🔴 RAW REQUEST BODY:")
    raw_body = await request.body()
    print(raw_body)

    print("\n🟢 PARSED DATA (Pydantic):")
    print(data)

    print("\n🟡 DICT DATA:")
    print(data.dict())

    print("\n🔵 USER INFO:")
    print(user)
    # ================= DEBUG END ===================


    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    cols = get_collections()
    clients_collection = cols["clients"]
    projects_collection = cols["projects_client"]
    industries_collection = cols["industries"]

    # ================= DEBUG =================
    print("\n🔍 Checking client:", data.client_name)
    # ========================================

    # 1. VALIDATE CLIENT
    existing_client = await clients_collection.find_one({
        "client_name": data.client_name
    })

    print("👉 existing_client:", existing_client)

    if not existing_client:
        raise HTTPException(400, "Invalid client name")

    client_code = existing_client["client_code"]

    # ================= DEBUG =================
    print("👉 client_code:", client_code)
    # ========================================

    # 2. USER LIMIT
    user_count = await clients_collection.count_documents({
        "client_code": client_code
    })

    print("👉 user_count:", user_count)

    if user_count >= 10:
        raise HTTPException(400, "Maximum 10 users allowed for this client")

    # 3. EMAIL CHECK
    existing_user = await clients_collection.find_one({
        "email_id": data.email_id
    })

    print("👉 existing_user:", existing_user)

    if existing_user:
        raise HTTPException(400, "Email already registered")

    # 4. GET INDUSTRY ID
    industry_doc = await industries_collection.find_one({
        "industry_name": data.industry_name
    })

    print("👉 industry_doc:", industry_doc)

    if not industry_doc:
        raise HTTPException(400, "Invalid industry name")

    industry_id = industry_doc["_id"]

    # ================= DEBUG =================
    print("👉 industry_id:", industry_id)
    # ========================================

    # 5. VALIDATE INDUSTRY ↔ CLIENT
    client_records = await clients_collection.find({
        "client_name": data.client_name
    }).to_list(None)

    client_ids = [c["_id"] for c in client_records]

    print("👉 client_ids:", client_ids)

    valid_project = await projects_collection.find_one({
        "industry_id": industry_id,
        "client_id": {"$in": client_ids}
    })

    print("👉 valid_project:", valid_project)

    if not valid_project:
        raise HTTPException(
            status_code=400,
            detail="Industry not mapped to selected client"
        )

    # =====================================================
    # ✅ INSERT ADMIN
    # =====================================================
    new_admin = {
        "admin_name": data.name,

        "client_code": client_code,
        "client_name": data.client_name,
        "industry_name": data.industry_name,

        "email_id": data.email_id,
        "password": data.password,

        "role": "admin",
        "status": "Active",

        "logo_path": existing_client.get("logo_path", ""),

        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    print("\n🟣 FINAL DOCUMENT TO INSERT:")
    print(new_admin)

    result = await clients_collection.insert_one(new_admin)

    print("✅ INSERTED ID:", result.inserted_id)

    # =====================================================
    # ✅ RESPONSE
    # =====================================================
    return {
        "status": "success",
        "message": "Admin registered successfully",
        "data": {
            "Client Name": data.client_name,
            "Industry Name": data.industry_name,
            "Name": data.name,
            "Email": data.email_id
        }
    }