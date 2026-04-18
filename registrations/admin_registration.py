from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, root_validator
from datetime import datetime

from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["Registrations"])


# =========================================================
# 📦 SCHEMA (Flexible for frontend)
# =========================================================
class AdminRegisterRequest(BaseModel):
    client_name: str | None = None
    industry_name: str | None = None
    name: str | None = None
    email_id: EmailStr | None = None
    password: str | None = None

    @root_validator(pre=True)
    def map_fields(cls, values):
        return {
            "client_name": values.get("Client Name") or values.get("client_name"),
            "industry_name": values.get("Industry Name") or values.get("industry_name"),
            "name": values.get("Name") or values.get("name"),
            "email_id": values.get("Email") or values.get("email") or values.get("email_id"),
            "password": values.get("Password") or values.get("password"),
        }


# =========================================================
# 🚀 POST API → REGISTER ADMIN
# =========================================================
@router.post("/register")
async def register_admin(
    request: Request,
    data: AdminRegisterRequest,
    user=Depends(get_current_user)
):

    # ================= DEBUG =================
    print("\n🔴 RAW REQUEST BODY:")
    print(await request.body())

    print("\n🟢 PARSED DATA:")
    print(data)

    print("\n🟡 DICT DATA:")
    print(data.dict())
    # ========================================

    # 🔐 AUTH CHECK
    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # ❗ REQUIRED FIELD CHECK
    if not all([data.client_name, data.industry_name, data.name, data.email_id, data.password]):
        raise HTTPException(status_code=400, detail="All fields are required")

    cols = get_collections()
    clients_collection = cols["clients"]
    projects_collection = cols["projects_client"]
    industries_collection = cols["industries"]

    # =====================================================
    # 1. VALIDATE CLIENT
    # =====================================================
    existing_client = await clients_collection.find_one({
        "client_name": data.client_name
    })

    print("👉 existing_client:", existing_client)

    if not existing_client:
        raise HTTPException(400, "Invalid client name")

    client_code = existing_client["client_code"]

    # =====================================================
    # 2. USER LIMIT
    # =====================================================
    user_count = await clients_collection.count_documents({
        "client_code": client_code
    })

    print("👉 user_count:", user_count)

    if user_count >= 10:
        raise HTTPException(400, "Maximum 10 users allowed for this client")

    # =====================================================
    # 3. EMAIL CHECK
    # =====================================================
    existing_user = await clients_collection.find_one({
        "email_id": data.email_id
    })

    print("👉 existing_user:", existing_user)

    if existing_user:
        raise HTTPException(400, "Email already registered")

    # =====================================================
    # 4. INDUSTRY VALIDATION (ONLY VALIDATE, NOT STORE)
    # =====================================================
    industry_doc = await industries_collection.find_one({
        "industry_name": data.industry_name
    })

    print("👉 industry_doc:", industry_doc)

    if not industry_doc:
        raise HTTPException(400, "Invalid industry name")

    industry_id = industry_doc["_id"]

    # =====================================================
    # 5. VALIDATE INDUSTRY ↔ CLIENT
    # =====================================================
    client_records = await clients_collection.find({
        "client_name": data.client_name
    }).to_list(None)

    client_ids = [c["_id"] for c in client_records]

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
    # ✅ INSERT ADMIN (STRICT — NO industry_name)
    # =====================================================
    new_admin = {
        "admin_name": data.name,

        "client_code": client_code,
        "client_name": data.client_name,

        # ❌ industry_name NOT stored

        "email_id": data.email_id,
        "password": data.password,  # ⚠️ hash in production

        "role": "admin",
        "status": "Active",

        "logo_path": existing_client.get("logo_path", ""),

        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    print("\n🟣 FINAL DOCUMENT:")
    print(new_admin)

    result = await clients_collection.insert_one(new_admin)

    print("✅ INSERTED ID:", result.inserted_id)

    # =====================================================
    # ✅ RESPONSE (FRONTEND FORMAT)
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