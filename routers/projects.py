from fastapi import APIRouter
from utils.mongo_serializer import serialize_mongo
from fastapi import Depends
from auth.dependencies import get_current_user
from database import get_collections
from fastapi.encoders import jsonable_encoder
from bson import ObjectId


router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("/")
async def get_projects(user=Depends(get_current_user)):
    cols = get_collections()
    projects = await cols["projects_master"].find().to_list(100)

    return jsonable_encoder(
        projects,
        custom_encoder={ObjectId: str}
    )


