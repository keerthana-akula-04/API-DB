from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime

from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["Registrations"])


# =========================================================
# 📦 SCHEMA
# =========================================================
class AdminRegisterRequest(BaseModel):
    client_name: str
    industry_name: str
    email_id: EmailStr
    password: str


# =========================================================
# 🔹 GET API → DROPDOWN DATA
# =========================================================
@router.get("/data")
async def get_admin_form_data(user=Depends(get_current_user)):

    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    cols = get_collections()
    clients_collection = cols["clients"]
    projects_collection = cols["projects_client"]
    industries_collection = cols["industries"]

    clients = await clients_collection.find().to_list(None)
    projects = await projects_collection.find().to_list(None)
    industries = await industries_collection.find().to_list(None)

    # 🔹 Industry map
    industry_map = {
        str(ind["_id"]): ind["industry_name"]
        for ind in industries
    }

    # 🔹 Group clients
    client_map = {}

    for c in clients:
        name = c["client_name"]

        if name not in client_map:
            client_map[name] = {"client_ids": []}

        client_map[name]["client_ids"].append(c["_id"])

    result = []

    # 🔹 Map client → industries
    for client_name, data in client_map.items():

        industries_list = []

        for p in projects:
            if p["client_id"] in data["client_ids"]:

                industry_id = str(p.get("industry_id"))
                industry_name = industry_map.get(industry_id)

                if industry_name:
                    industries_list.append(industry_name)

        result.append({
            "client_name": client_name,
            "industries": list(set(industries_list))
        })

    return {
        "status": "success",
        "data": result
    }


# =========================================================
# 🚀 POST API → REGISTER ADMIN
# =========================================================
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
    industries_collection = cols["industries"]

    # 1. VALIDATE CLIENT
    existing_client = await clients_collection.find_one({
        "client_name": data.client_name
    })

    if not existing_client:
        raise HTTPException(400, "Invalid client name")

    client_code = existing_client["client_code"]
    admin_name = existing_client.get("admin_name", "")  # Get from existing client
    logo_path = existing_client.get("logo_path", "")    # Get from existing client

    # 2. USER LIMIT
    user_count = await clients_collection.count_documents({
        "client_code": client_code
    })

    if user_count >= 10:
        raise HTTPException(400, "Maximum 10 users allowed for this client")

    # 3. EMAIL CHECK
    existing_user = await clients_collection.find_one({
        "email_id": data.email_id
    })

    if existing_user:
        raise HTTPException(400, "Email already registered")

    # 4. GET INDUSTRY ID
    industry_doc = await industries_collection.find_one({
        "industry_name": data.industry_name
    })

    if not industry_doc:
        raise HTTPException(400, "Invalid industry name")

    industry_id = industry_doc["_id"]

    # 5. VALIDATE INDUSTRY ↔ CLIENT
    client_records = await clients_collection.find({
        "client_name": data.client_name
    }).to_list(None)

    client_ids = [c["_id"] for c in client_records]

    valid_project = await projects_collection.find_one({
        "industry_id": industry_id,
        "client_id": {"$in": client_ids}
    })

    if not valid_project:
        raise HTTPException(
            status_code=400,
            detail="Industry not mapped to selected client"
        )

    # =====================================================
    # ✅ INSERT ADMIN (with industry_name, admin_name, logo_path)
    # =====================================================
    new_admin = {
        "client_code": client_code,
        "client_name": data.client_name,
        "industry_name": data.industry_name,
        "email_id": data.email_id,
        "password": data.password,
        "role": "admin",
        "status": "Active",
        "admin_name": admin_name,
        "logo_path": logo_path,
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
            "adminName": admin_name,
            "logoPath": logo_path,
            "email": data.email_id
        }
    }