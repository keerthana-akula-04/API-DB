from fastapi import APIRouter
from database import get_collections
from bson import ObjectId
from utils.mongo_serializer import serialize_mongo
from fastapi import Depends
from auth.dependencies import get_current_user

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# ===============================
# Helper: Convert ObjectId to String
# ===============================
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


# ===============================
# GET ALERTS
# ===============================
@router.get("/")
async def get_alerts(user=Depends(get_current_user)):
    cols = get_collections()

    alerts = await cols["alerts"].find().sort("_id", -1).to_list(None)
    return serialize_mongo(alerts)
