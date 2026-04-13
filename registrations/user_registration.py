from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, EmailStr
from database import db

router = APIRouter()

# =========================================================
# 📦 SCHEMA (Fixes Swagger + Matches Frontend Fields)
# =========================================================
class UserRegister(BaseModel):
    user_name: str = Field(..., alias="User Name")
    contact_name: str = Field(..., alias="Contact Name")
    email: EmailStr = Field(..., alias="Email")
    password: str = Field(..., alias="Password")

    class Config:
        populate_by_name = True


class SuperAdminUserRegister(UserRegister):
    client_name: str = Field(..., alias="Client Name")


# =========================================================
# 🔹 COMMON FUNCTION
# =========================================================
def create_user_common(data, client_code):

    # ✅ Check client exists
    client = db.admins.find_one({"client_code": client_code})
    if not client:
        return {"error": "Invalid client"}

    client_name = client["client_name"]

    # 🔍 Check duplicate email
    existing = db.users.find_one({"email": data.email})
    if existing:
        return {"error": "User already exists"}

    # 📦 Insert user
    user_data = {
        "client_code": client_code,
        "client_name": client_name,
        "user_name": data.user_name,
        "contact_name": data.contact_name,
        "email": data.email,
        "password": data.password,
        "role": "user",
        "status": "Active"
    }

    db.users.insert_one(user_data)

    return {
        "message": "User registered successfully",
        "client_name": client_name
    }


# =========================================================
# 🥇 SUPERADMIN USER REGISTRATION
# =========================================================
@router.post("/superadmin/register-user")
def superadmin_register_user(data: SuperAdminUserRegister):

    # 🔍 Find client using name
    client = db.admins.find_one({"client_name": data.client_name})
    if not client:
        return {"error": "Client not found"}

    return create_user_common(
        data=data,
        client_code=client["client_code"]
    )


# =========================================================
# 🥈 ADMIN USER REGISTRATION (AUTO CLIENT FROM HEADERS)
# =========================================================
@router.post("/admin/register-user")
def admin_register_user(request: Request, data: UserRegister):

    # 🔥 Get client from headers (after login)
    client_code = request.headers.get("client_code")
    role = request.headers.get("role")

    # 🚫 Only admin allowed
    if role != "admin":
        return {"error": "Only admin can create users"}

    if not client_code:
        return {"error": "Client code missing in headers"}

    return create_user_common(
        data=data,
        client_code=client_code
    )