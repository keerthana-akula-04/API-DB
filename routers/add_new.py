from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from datetime import datetime
from database import db
import cloudinary
import cloudinary.uploader

router = APIRouter()

# ---------------------------
# Cloudinary Configuration
# ---------------------------

cloudinary.config(
    cloud_name="your_cloud_name",
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# ---------------------------
# Helper Functions
# ---------------------------

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
        "deliverable_img_path": "",   # required field
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

# ---------------------------
# GET /add-new
# ---------------------------

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

# ---------------------------
# POST /add-new
# ---------------------------

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

    # Validate role
    if role not in ["super_admin", "admin", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    # Validate email
    if "@" not in email_id:
        raise HTTPException(status_code=400, detail="Invalid email")

    # Validate logo format
    if not logo.filename.lower().endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Logo must be .jpg")

    # ---------------------------
    # Upload Logo
    # ---------------------------

    logo_upload = cloudinary.uploader.upload(
        await logo.read(),
        folder="add_new/logos"
    )

    logo_url = logo_upload["secure_url"]

    # ---------------------------
    # Upload Project Files
    # ---------------------------

    uploaded_files = []

    for file in files:

        result = cloudinary.uploader.upload(
            await file.read(),
            folder=f"add_new/projects/{project_name}",
            resource_type="auto"
        )

        uploaded_files.append(result["secure_url"])

    # ---------------------------
    # CLIENT LOGIC
    # ---------------------------

    existing_client = db.clients.find_one({"email_id": email_id})

    if not existing_client:

        last_client = db.clients.find_one({}, sort=[("client_code", -1)])

        number = 1
        if last_client and "client_code" in last_client:
            try:
                number = int(last_client["client_code"].split("_")[1]) + 1
            except:
                number = 1

        client_doc = build_client_doc(
            client_name,
            email_id,
            password,
            role,
            logo_url,
            number
        )

        db.clients.insert_one(client_doc)

    else:

        db.clients.update_one(
            {"_id": existing_client["_id"]},
            {
                "$set": {
                    "client_name": client_name,
                    "password": password,
                    "role": role,
                    "logo_path": logo_url,
                    "updated_at": datetime.utcnow()
                }
            }
        )

    # ---------------------------
    # INDUSTRY LOGIC
    # ---------------------------

    industry = db.industries.find_one({"industry_name": industry_name})

    if not industry:

        result = db.industries.insert_one(
            build_industry_doc(industry_name)
        )

        industry_id = result.inserted_id

    else:

        industry_id = industry["_id"]

    # ---------------------------
    # PROJECT MASTER
    # ---------------------------

    project = db.projects_master.find_one({"project_name": project_name})

    if not project:

        last_project = db.projects_master.find_one({}, sort=[("project_code", -1)])

        number = 1
        if last_project:
            try:
                number = int(last_project["project_code"].split("_")[1]) + 1
            except:
                number = 1

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

    # ---------------------------
    # DELIVERABLE
    # ---------------------------

    deliverable = db.deliverables.find_one(
        {"deliverable_name": deliverable_name}
    )

    if not deliverable:

        last_deliverable = db.deliverables.find_one(
            {},
            sort=[("deliverable_code", -1)]
        )

        number = 1
        if last_deliverable:
            try:
                number = int(last_deliverable["deliverable_code"].split("_")[1]) + 1
            except:
                number = 1

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