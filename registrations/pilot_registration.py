from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/pilot", tags=["Registrations"])


# =========================================================
# 📦 SCHEMA
# =========================================================
class PilotRegisterRequest(BaseModel):
    client_name: str = Field(..., alias="Client Name")
    industry_name: str = Field(..., alias="Industry Name")
    pilot_name: str = Field(..., alias="Pilot Name")

    drone_category: str = Field(..., alias="Drone Category")

    small_license_id: str | None = Field(None, alias="Small License ID")
    medium_license_id: str | None = Field(None, alias="Medium License ID")

    license_number: str = Field(..., alias="License Number")

    email_id: EmailStr = Field(..., alias="Email")
    password: str = Field(..., alias="Password")

    class Config:
        populate_by_name = True


# =========================================================
# 🔹 GET API → DROPDOWN DATA
# =========================================================
@router.get("/data")
async def get_pilot_form_data(user=Depends(get_current_user)):

    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    cols = get_collections()
    clients_collection = cols["clients"]
    projects_collection = cols["projects_client"]
    industries_collection = cols["industries"]

    clients = await clients_collection.find().to_list(None)
    projects = await projects_collection.find().to_list(None)
    industries = await industries_collection.find().to_list(None)

    # Industry map
    industry_map = {
        str(ind["_id"]): ind["industry_name"]
        for ind in industries
    }

    # Group client_ids
    client_map = {}

    for c in clients:
        name = c["client_name"]

        if name not in client_map:
            client_map[name] = {"client_ids": []}

        client_map[name]["client_ids"].append(c["_id"])

    result = []

    # Map client → industries
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
        "data": {
            "clients": result,
            "drone_categories": ["Small", "Medium", "Hybrid"]
        }
    }


# =========================================================
# 🚀 POST API → REGISTER PILOT
# =========================================================
@router.post("/register")
async def register_pilot(
    data: PilotRegisterRequest,
    user=Depends(get_current_user)
):

    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

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

    if not existing_client:
        raise HTTPException(400, "Invalid client name")

    client_code = existing_client["client_code"]

    # =====================================================
    # 2. USER LIMIT
    # =====================================================
    user_count = await clients_collection.count_documents({
        "client_code": client_code
    })

    if user_count >= 10:
        raise HTTPException(400, "Maximum 10 users allowed for this client")

    # =====================================================
    # 3. EMAIL CHECK
    # =====================================================
    existing_user = await clients_collection.find_one({
        "email_id": data.email_id
    })

    if existing_user:
        raise HTTPException(400, "Email already registered")

    # =====================================================
    # 4. GET INDUSTRY
    # =====================================================
    industry_doc = await industries_collection.find_one({
        "industry_name": data.industry_name
    })

    if not industry_doc:
        raise HTTPException(400, "Invalid industry name")

    industry_id = industry_doc["_id"]

    # =====================================================
    # 5. VALIDATE CLIENT ↔ INDUSTRY
    # =====================================================
    client_records = await clients_collection.find({
        "client_name": data.client_name
    }).to_list(None)

    client_ids = [c["_id"] for c in client_records]

    valid_project = await projects_collection.find_one({
        "industry_id": industry_id,
        "client_id": {"$in": client_ids}
    })

    if not valid_project:
        raise HTTPException(400, "Industry not mapped to selected client")

    # =====================================================
    # 6. PASSWORD VALIDATION
    # =====================================================
    if len(data.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    # =====================================================
    # 7. LICENSE NUMBER VALIDATION
    # =====================================================
    if not data.license_number:
        raise HTTPException(400, "License Number is required")

    # =====================================================
    # 8. DRONE CATEGORY LOGIC
    # =====================================================
    category = data.drone_category.strip().lower()

    if category not in ["small", "medium", "hybrid"]:
        raise HTTPException(400, "Invalid drone category")

    small_license = None
    medium_license = None

    if category == "small":
        if not data.small_license_id:
            raise HTTPException(400, "Small License ID required")
        small_license = data.small_license_id

    elif category == "medium":
        if not data.medium_license_id:
            raise HTTPException(400, "Medium License ID required")
        medium_license = data.medium_license_id

    elif category == "hybrid":
        if not data.small_license_id or not data.medium_license_id:
            raise HTTPException(
                400, "Both Small and Medium License IDs required"
            )
        small_license = data.small_license_id
        medium_license = data.medium_license_id

    # =====================================================
    # 9. BUILD DATA (NO NULL FIELDS)
    # =====================================================
    new_pilot = {
        "client_code": client_code,
        "client_name": data.client_name,

        "email_id": data.email_id,
        "password": data.password,

        "role": "pilot",
        "status": "Active",

        "pilot_name": data.pilot_name,
        "drone_category": category,

        "license_number": data.license_number,

        "logo_path": existing_client.get("logo_path", ""),

        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    # ✅ ONLY ADD IF EXISTS (FIX APPLIED)
    if small_license:
        new_pilot["small_license_number"] = small_license

    if medium_license:
        new_pilot["medium_license_number"] = medium_license

    # =====================================================
    # 10. INSERT
    # =====================================================
    result = await clients_collection.insert_one(new_pilot)

    # =====================================================
    # 11. RESPONSE
    # =====================================================
    return {
        "status": "success",
        "message": "Pilot registered successfully",
        "data": {
            "pilotId": str(result.inserted_id),
            "clientName": data.client_name,
            "pilotName": data.pilot_name,
            "industryName": data.industry_name,
            "email": data.email_id
        }
    }