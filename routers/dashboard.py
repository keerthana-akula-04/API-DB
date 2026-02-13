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

# ================= GET NOTIFICATIONS =================
@router.get("/notifications")
async def get_notifications(user=Depends(get_current_user)):
    cols = get_collections()

    notifications = await cols["notifications"].find().sort("created_at", -1).to_list(None)


    # Convert ObjectId to string
    return serialize_mongo(notifications)
