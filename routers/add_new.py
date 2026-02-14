from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from database import db
import cloudinary
import cloudinary.uploader
import json
import os
from datetime import datetime

router = APIRouter()

DATA_FILE = "data/add_new_data.json"

# ==============================
# Cloudinary Config
# ==============================

cloudinary.config(
    cloud_name="your_cloud_name",
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# ==============================
# CREATE JSON FROM DB IF NOT EXISTS
# ==============================

def create_json_from_db():
    clients = list(db.clients.find({}, {"_id": 0, "client_name": 1}))
    industries = list(db.industries.find({}, {"_id": 0, "industry_name": 1}))
    deliverables = list(db.deliverables.find({}, {"_id": 0, "deliverable_name": 1}))
    projects_master = list(db.projects_master.find(
        {},
        {
            "_id": 0,
            "project_name": 1,
            "location_name": 1,
            "location_url": 1
        }
    ))

    formatted_data = {
        "clients": [c["client_name"] for c in clients],
        "industries": [i["industry_name"] for i in industries],
        "deliverables": [d["deliverable_name"] for d in deliverables],
        "projects_master": projects_master,
        "projects": []
    }

    os.makedirs("data", exist_ok=True)

    with open(DATA_FILE, "w") as f:
        json.dump(formatted_data, f, indent=4)


# ==============================
# GET ADD-NEW
# ==============================

@router.get("/add-new")
def get_add_new():

    if not os.path.exists(DATA_FILE):
        create_json_from_db()

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    return {
        "status": "success",
        "data": data
    }


# ==============================
# POST ADD-NEW
# ==============================

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

    # Validate logo
    if not logo.filename.lower().endswith(".jpg"):
        raise HTTPException(
            status_code=400,
            detail="Logo must be in .jpg format only"
        )

    # Upload logo
    logo_upload = cloudinary.uploader.upload(
        await logo.read(),
        folder="add_new/logos"
    )
    logo_url = logo_upload["secure_url"]

    # Upload files
    uploaded_files = []

    for file in files:
        upload_result = cloudinary.uploader.upload(
            await file.read(),
            folder=f"add_new/projects/{project_name}",
            resource_type="auto"
        )
        uploaded_files.append(upload_result["secure_url"])

    # Ensure JSON exists
    if not os.path.exists(DATA_FILE):
        create_json_from_db()

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    # Update JSON (clean only)
    if client_name not in data["clients"]:
        data["clients"].append(client_name)

    if industry_name not in data["industries"]:
        data["industries"].append(industry_name)

    if deliverable_name not in data["deliverables"]:
        data["deliverables"].append(deliverable_name)

    new_master_project = {
        "project_name": project_name,
        "location_name": location_name,
        "location_url": location_url
    }

    if new_master_project not in data["projects_master"]:
        data["projects_master"].append(new_master_project)

    data["projects"].append({
        "client_name": client_name,
        "industry_name": industry_name,
        "deliverable_name": deliverable_name,
        "project_name": project_name,
        "location_name": location_name,
        "location_url": location_url,
        "logo_url": logo_url,
        "files": uploaded_files,
        "created_at": datetime.utcnow().isoformat()
    })

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

    # ==============================
    # INSERT INTO DB
    # ==============================

    try:
        # CLIENT
existing_client = db.clients.find_one({"client_name": client_name})

if not existing_client:
    last = db.clients.find_one({}, sort=[("client_code", -1)])
    number = 1
    if last and "client_code" in last:
        try:
            number = int(last["client_code"].split("_")[1]) + 1
        except:
            number = 1

    db.clients.insert_one({
        "client_code": f"C_{number}",
        "client_name": client_name,
        "email_id": email_id,        # ✅ Original value
        "password": password,        # ✅ Original value
        "role": role,                # ✅ Original value
        "status": "Active",
        "created_at": datetime.utcnow()
    })

        

        # INDUSTRY
        existing_industry = db.industries.find_one({"industry_name": industry_name})
        if not existing_industry:
            db.industries.insert_one({
                "industry_code": industry_name[:3].upper(),
                "industry_name": industry_name,
                "created_at": datetime.utcnow()
            })

        industry = db.industries.find_one({"industry_name": industry_name})
        industry_id = industry["_id"]

        # PROJECT MASTER
        existing_project = db.projects_master.find_one({"project_name": project_name})
        if not existing_project:
            last = db.projects_master.find_one({}, sort=[("project_code", -1)])
            number = 1
            if last:
                number = int(last["project_code"].split("_")[1]) + 1

            db.projects_master.insert_one({
                "project_code": f"PRJ_{number}",
                "project_name": project_name,
                "location_name": location_name,
                "location_url": location_url,
                "industry_id": industry_id,
                "status": "Planning",
                "created_at": datetime.utcnow()
            })

        project = db.projects_master.find_one({"project_name": project_name})
        project_id_db = project["_id"]

        # DELIVERABLE
        existing_deliverable = db.deliverables.find_one({
            "deliverable_name": deliverable_name
        })

        if not existing_deliverable:
            last = db.deliverables.find_one({}, sort=[("deliverable_code", -1)])
            number = 1
            if last:
                number = int(last["deliverable_code"].split("_")[1]) + 1

            db.deliverables.insert_one({
                "deliverable_code": f"DEL_{number}",
                "deliverable_name": deliverable_name,
                "project_id": project_id_db,
                "industry_id": industry_id,
                "created_at": datetime.utcnow()
            })

    except Exception as e:
        print("DB INSERT ERROR:", e)

    return {
        "message": "Project added successfully"
    }
