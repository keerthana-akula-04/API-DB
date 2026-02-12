from fastapi import APIRouter
from database import get_collections
from utils.mongo_serializer import serialize_mongo
from fastapi import Depends
from auth.dependencies import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/")
async def get_reports(user=Depends(get_current_user)):
    cols = get_collections()
    data = await cols["reports"].find().to_list(None)

    return serialize_mongo(data)
