from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.dashboard_service import build_dashboard_response
from database import get_collections
from bson import ObjectId
from datetime import datetime
from utils.mongo_serializer import serialize_mongo
import uuid
import cloudinary.uploader
from fastapi import Depends
from auth.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ==========================
# HELPER: Serialize ObjectId
# ==========================
def serialize_mongo(document):
    if isinstance(document, list):
        return [serialize_mongo(doc) for doc in document]

    if isinstance(document, dict):
        new_doc = {}
        for key, value in document.items():
            if isinstance(value, ObjectId):
                new_doc[key] = str(value)
            else:
                new_doc[key] = value
        return new_doc

    return document


# ================= DASHBOARD SUMMARY =================
@router.get("/")
async def get_dashboard(user=Depends(get_current_user)):
    return await build_dashboard_response()


# ================= UPLOAD PROJECT =================
@router.post("/uploads")
async def upload_project(
    client_name: str = Form(...),
    industry: str = Form(...),
    deliverable: str = Form(...),
    project: str = Form(...),
    site_name: str = Form(...),
    site_location_map: str = Form(...),
    logo: UploadFile = File(...),
    overview: UploadFile = File(...)
):
    if "google.com" not in site_location_map:
        raise HTTPException(status_code=400, detail="Invalid Google Maps URL")

    cols = get_collections()

    # Upload to Cloudinary
    logo_url = cloudinary.uploader.upload(
        await logo.read(),
        folder="project_logos",
        public_id=f"{uuid.uuid4()}_{logo.filename}"
    )["secure_url"]

    overview_url = cloudinary.uploader.upload(
        await overview.read(),
        folder="project_overviews",
        public_id=f"{uuid.uuid4()}_{overview.filename}"
    )["secure_url"]

    record = {
        "client_name": client_name,
        "industry": industry,
        "deliverable": deliverable,
        "project": project,
        "site_name": site_name,
        "site_location_map": site_location_map,
        "logo_url": logo_url,
        "overview_url": overview_url
    }

    # Insert into projects collection
    await cols["projects_col"].insert_one(record)    

    return {
        "status": "success",
        "message": "Project uploaded successfully"
    }

# ================= GET NOTIFICATIONS =================
@router.get("/notifications")
async def get_notifications(user=Depends(get_current_user)):
    cols = get_collections()

    notifications = await cols["notifications"].find().sort("created_at", -1).to_list(None)


    # Convert ObjectId to string
    return serialize_mongo(notifications)
