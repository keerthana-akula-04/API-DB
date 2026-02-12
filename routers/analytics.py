from fastapi import APIRouter, Query, HTTPException
from database import get_collections
from utils.mongo_serializer import serialize_mongo
from fastapi import Depends
from auth.dependencies import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ================= GET ANALYTICS =================
@router.get("/")
async def get_latest_analytics(user=Depends(get_current_user)):
    cols = get_collections()

    analytics = await cols["analytics"].find().sort("created_at", 1).limit(1).to_list(1)

    if not analytics:
        return {"message": "No analytics found"}

    return serialize_mongo(analytics[0])
