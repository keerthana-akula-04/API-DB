from fastapi import APIRouter
from utils.mongo_serializer import serialize_mongo
from fastapi import Depends
from auth.dependencies import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("/")
async def get_projects(user=Depends(get_current_user)):
    cols = get_collections()
    return await cols["projects_col"].find({}, {"_id": 0}).to_list(None)
