from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from datetime import datetime
from database import db
import cloudinary
import cloudinary.uploader

router = APIRouter()

ALLOWED_ROLES = ["super_admin", "admin", "user", "pilot"]

cloudinary.config(
    cloud_name="your_cloud_name",
    api_key="your_api_key",
    api_secret="your_api_secret"
)

def validate_role(role: str):
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")


def validate_email(email: str):
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")


def validate_logo(logo: UploadFile):
    if not logo.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(status_code=400, detail="Logo must be JPG/PNG")


def build_client_doc(client_name, email_id, password, role, logo_url, number):
    return {
        "client_code": f"C_{number}",
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


def build_project_doc(project_name, location_name, location_url, industry_id, number):
    return {
        "project_code": f"PRJ_{number}",
        "project_name": project_name,
        "project_image_path": "",
        "location_name": location_name,
        "location_url": location_url,
        "industry_id": industry_id,
        "status": "Planning",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


def build_deliverable_doc(deliverable_name, project_id, industry_id, number):
    return {
        "deliverable_code": f"DEL_{number}",
        "deliverable_name": deliverable_name,
        "project_id": project_id,
        "industry_id": industry_id,
        "deliverable_img_path": "",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


def get_next_sequence(collection, field_prefix):
    last = collection.find_one({}, sort=[(field_prefix, -1)])
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

# GET /add-new 
@router.get("/add-new")
def get_add_new():

    clients = list(db.clients.find({}, {"_id": 0, "client_name": 1}))
    industries = list(db.industries.find({}, {"_id": 0, "industry_name": 1}))
    deliverables = list(db.deliverables.find({}, {"_id": 0, "deliverable_name": 1}))

    projects_master = list(
        db.projects_master.find(
            {},
            {
                "_id": 0,
                "project_name": 1,
                "location_name": 1,
                "location_url": 1
            }
        )
    )

    return {
        "status": "success",
        "data": {
            "clients": [c["client_name"] for c in clients],
            "industries": [i["industry_name"] for i in industries],
            "deliverables": [d["deliverable_name"] for d in deliverables],
            "projects_master": projects_master
        }
    }

# POST /add-new

@router.post("/add-new")
async def add_new_project(
    client_name: str = Form(...),
    email_id: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    industry_name: str = Form(...),
    deliverable_name: str = Form(...),
    project_name: str = Form(...),
    location_name: str = Form(...),
    location_url: str = Form(...),
    logo: UploadFile = File(...),
    files: list[UploadFile] = File(...)
):

    # VALIDATION
    validate_role(role)
    validate_email(email_id)
    validate_logo(logo)

    # CHECK UNIQUE EMAIL 
    existing_client = db.clients.find_one({"email_id": email_id})

    if existing_client:
        raise HTTPException(
            status_code=409,
            detail="User with this email already exists"
        )

    # UPLOAD LOGO
    logo_url = await upload_to_cloudinary(logo, "add_new/logos")

    # UPLOAD FILES
    uploaded_files = []

    for file in files:
        file_url = await upload_to_cloudinary(
            file,
            f"add_new/projects/{project_name}"
        )
        uploaded_files.append(file_url)

    # CLIENT INSERT
    number = get_next_sequence(db.clients, "client_code")

    db.clients.insert_one(
        build_client_doc(
            client_name,
            email_id,
            password,
            role,
            logo_url,
            number
        )
    )

    # INDUSTRY
    industry = db.industries.find_one({"industry_name": industry_name})

    if not industry:
        result = db.industries.insert_one(
            build_industry_doc(industry_name)
        )
        industry_id = result.inserted_id
    else:
        industry_id = industry["_id"]

    # PROJECT
    project = db.projects_master.find_one({"project_name": project_name})

    if not project:
        number = get_next_sequence(db.projects_master, "project_code")

        result = db.projects_master.insert_one(
            build_project_doc(
                project_name,
                location_name,
                location_url,
                industry_id,
                number
            )
        )
        project_id = result.inserted_id
    else:
        project_id = project["_id"]

    # DELIVERABLE
    deliverable = db.deliverables.find_one(
        {"deliverable_name": deliverable_name}
    )

    if not deliverable:
        number = get_next_sequence(db.deliverables, "deliverable_code")

        db.deliverables.insert_one(
            build_deliverable_doc(
                deliverable_name,
                project_id,
                industry_id,
                number
            )
        )

    return {
        "message": "Project added successfully",
        "uploaded_files": uploaded_files
    }


@router.post("/register-pilot")
async def register_pilot(
    pilot_name: str = Form(...),
    email_id: str = Form(...),
    password: str = Form(...),
    contact_number: str = Form(...),
    license_number: str = Form(...)
):

    role = "pilot"

    # VALIDATIONS
    validate_role(role)
    validate_email(email_id)

    # CHECK DUPLICATE EMAIL
    existing_client = db.clients.find_one({"email_id": email_id})
    if existing_client:
        raise HTTPException(
            status_code=409,
            detail="Pilot with this email already exists"
        )

    # GENERATE CLIENT CODE
    number = get_next_sequence(db.clients, "client_code")

    # BUILD DOCUMENT (AS PER YOUR CURRENT DB)
    pilot_doc = {
        "client_code": f"C_{number}",
        "client_name": "",  # optional or keep empty
        "pilot_name": pilot_name,  # ✅ important field
        "email_id": email_id,
        "password": password,
        "role": role,
        "contact_number": contact_number,
        "license_number": license_number,
        "status": "Active",
        "logo_path": "",  # pilot may not have logo
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    db.clients.insert_one(pilot_doc)

    return {
        "message": "Pilot registered successfully",
        "client_code": pilot_doc["client_code"]
    }