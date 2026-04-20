from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from datetime import datetime
from typing import List, Optional
from database import get_collections
import cloudinary
import cloudinary.uploader

router = APIRouter()

ALLOWED_ROLES = ["super_admin", "admin", "user", "pilot"]

# ---------------- CLOUDINARY CONFIG ---------------- #

cloudinary.config(
    cloud_name="your_cloud_name",
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# ---------------- VALIDATIONS ---------------- #

def validate_role(role: str):
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")


def validate_email(email: str):
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")


def validate_logo(logo: UploadFile):
    if logo and not logo.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(status_code=400, detail="Logo must be JPG/PNG")


# ---------------- BUILD DOCS ---------------- #

def build_client_doc(client_name, email_id, password, role, logo_url, number):
    return {
        "client_code": f"C_{number:02d}",
        "client_name": client_name,
        "email_id": email_id,
        "password": password,
        "role": role,
        "status": "Active",
        "logo_path": logo_url,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


def build_industry_doc(industry_name):
    return {
        "industry_code": industry_name[:3].upper(),
        "industry_name": industry_name,
        "industry_image_url": "",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


def build_project_doc(project_name, location_name, location_url, industry_id, number, uploaded_files):
    return {
        "project_code": f"PRJ_{number:02d}",
        "project_name": project_name,
        "project_image_path": uploaded_files[0] if uploaded_files else "",
        "location_name": location_name,
        "location_url": location_url,
        "industry_id": industry_id,
        "status": "Planning",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


def build_deliverable_doc(deliverable_name, project_id, industry_id, number):
    return {
        "deliverable_code": f"DEL_{number:02d}",
        "deliverable_name": deliverable_name,
        "project_id": project_id,
        "industry_id": industry_id,
        "deliverable_img_path": "",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


# ---------------- HELPERS ---------------- #

async def get_next_sequence(collection, field_prefix):
    last = await collection.find_one({}, sort=[(field_prefix, -1)])
    number = 1

    if last:
        try:
            number = int(last[field_prefix].split("_")[1]) + 1
        except:
            number = 1

    return number


async def upload_to_cloudinary(file: UploadFile, folder: str):
    result = cloudinary.uploader.upload(
        await file.read(),
        folder=folder,
        resource_type="auto"
    )
    return result["secure_url"]


# ---------------- GET API ---------------- #

@router.get("/add-new")
async def get_add_new():

    collections = get_collections()

    clients = await collections["clients"].distinct("client_name")
    industries = await collections["industries"].distinct("industry_name")
    deliverables = await collections["deliverables"].distinct("deliverable_name")

    projects_master = await collections["projects_master"].find(
        {},
        {
            "_id": 0,
            "project_name": 1,
            "location_name": 1,
            "location_url": 1
        }
    ).to_list(length=None)

    return {
        "status": "success",
        "data": {
            "clients": clients,
            "industries": industries,
            "deliverables": deliverables,
            "projects_master": projects_master
        }
    }


# ---------------- POST API ---------------- #

@router.post("/add-new")
async def add_new_project(
    client_name: str = Form(...),

    email_id: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    role: Optional[str] = Form(None),

    industry_name: str = Form(...),
    deliverable_name: str = Form(...),
    project_name: str = Form(...),
    location_name: str = Form(...),
    location_url: str = Form(...),

    logo: Optional[UploadFile] = File(None),
    files: List[UploadFile] = File(default=[])
):

    collections = get_collections()

    # ---------------- CHECK CLIENT ---------------- #
    existing_client = await collections["clients"].find_one({
        "client_name": client_name
    })

    # ---------------- NEW CLIENT ---------------- #
    if not existing_client:

        if not email_id or not password or not role:
            raise HTTPException(
                status_code=400,
                detail="email_id, password and role are required for new client"
            )

        validate_role(role)
        validate_email(email_id)

        existing_email = await collections["clients"].find_one({"email_id": email_id})
        if existing_email:
            raise HTTPException(status_code=409, detail="Email already exists")

        validate_logo(logo)

        logo_url = None
        if logo:
            logo_url = await upload_to_cloudinary(logo, "add_new/logos")

        client_number = await get_next_sequence(collections["clients"], "client_code")

        client_result = await collections["clients"].insert_one(
            build_client_doc(client_name, email_id, password, role, logo_url, client_number)
        )
        client_id = client_result.inserted_id

    # ---------------- EXISTING CLIENT ---------------- #
    else:
        client_id = existing_client["_id"]

    # ---------------- UPLOAD PROJECT FILES ---------------- #
    uploaded_files = []
    for file in files:
        file_url = await upload_to_cloudinary(
            file,
            f"add_new/projects/{project_name}"
        )
        uploaded_files.append(file_url)

    # ---------------- INDUSTRY ---------------- #
    industry = await collections["industries"].find_one({"industry_name": industry_name})

    if not industry:
        result = await collections["industries"].insert_one(
            build_industry_doc(industry_name)
        )
        industry_id = result.inserted_id
    else:
        industry_id = industry["_id"]

    # ---------------- PROJECT ---------------- #
    project = await collections["projects_master"].find_one({"project_name": project_name})

    if not project:
        number = await get_next_sequence(collections["projects_master"], "project_code")

        result = await collections["projects_master"].insert_one(
            build_project_doc(
                project_name,
                location_name,
                location_url,
                industry_id,
                number,
                uploaded_files
            )
        )
        project_id = result.inserted_id
    else:
        project_id = project["_id"]

    # ---------------- DELIVERABLE ---------------- #
    deliverable = await collections["deliverables"].find_one(
        {"deliverable_name": deliverable_name}
    )

    if not deliverable:
        number = await get_next_sequence(collections["deliverables"], "deliverable_code")

        result = await collections["deliverables"].insert_one(
            build_deliverable_doc(
                deliverable_name,
                project_id,
                industry_id,
                number
            )
        )
        deliverable_id = result.inserted_id
    else:
        deliverable_id = deliverable["_id"]

    # ---------------- FINAL LINK ---------------- #
    await collections["projects_client"].insert_one({
        "client_id": client_id,
        "project_id": project_id,
        "industry_id": industry_id,
        "deliverable_id": deliverable_id,
        "project_name": project_name,
        "location": location_name,
        "location_url": location_url,
        "status": "Planning",
        "progress": 10,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })

    return {
        "message": "Project added successfully",
        "uploaded_files": uploaded_files
    }