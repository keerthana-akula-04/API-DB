from fastapi import APIRouter
from database import get_collections
from utils.mongo_serializer import serialize_mongo
from fastapi import Depends
from auth.dependencies import get_current_user

router = APIRouter(prefix="/admins", tags=["Admins"])

@router.get("/")
async def get_admins(user=Depends(get_current_user)):
    cols = get_collections()
    return await cols["admin_mgmt_col"].find({}, {"_id": 0}).to_list(None)
