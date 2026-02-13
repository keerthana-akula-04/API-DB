from fastapi import APIRouter, Depends, Query, HTTPException
from bson import ObjectId
from database import get_collections
from utils.mongo_serializer import serialize_mongo
from auth.dependencies import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ==========================================
# SINGLE DYNAMIC ANALYTICS ENDPOINT
# ==========================================
@router.get("/")
async def get_analytics(
    industry_id: str,
    project_id: str,
    deliverable_id: str,
    version: int,
    user=Depends(get_current_user)
):

    cols = get_collections()
    client_id = ObjectId(user["client_id"])

    # Find report first
    report = await cols["reports"].find_one({
        "client_id": client_id,
        "industry_id": ObjectId(industry_id),
        "project_id": ObjectId(project_id),
        "deliverable_id": ObjectId(deliverable_id),
        "version": version
    })

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    analytics = await cols["analytics"].find_one({
        "report_id": report["_id"]
    })

    if not analytics:
        raise HTTPException(status_code=404, detail="Analytics not found")

    return serialize_mongo(analytics)
