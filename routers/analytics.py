from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from database import get_collections
from utils.mongo_serializer import serialize_mongo
from auth.dependencies import get_current_user
from routers.reports import find_report_by_filters

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/")
async def get_analytics(
    industry_id: str,
    project_id: str,
    deliverable_id: str,
    version: int,
    user=Depends(get_current_user)
):
    cols = get_collections()

    report = await find_report_by_filters(
        cols,
        user,
        industry_id,
        project_id,
        deliverable_id,
        version
    )

    analytics = await cols["analytics"].find_one({
        "report_id": report["_id"]
    })

    if not analytics:
        raise HTTPException(status_code=404, detail="Analytics not found")

    return serialize_mongo(analytics)
