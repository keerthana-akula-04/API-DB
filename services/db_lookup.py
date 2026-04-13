from bson import ObjectId
from database import db 


async def get_industry_name(industry_id: str):
    try:
        industry = await db["industries"].find_one({"_id": ObjectId(industry_id)})
        return industry["name"] if industry else industry_id
    except Exception:
        return industry_id


async def get_project_name(project_id: str):
    try:
        project = await db["projects_master"].find_one({"_id": ObjectId(project_id)})  
        return project["name"] if project else project_id
    except Exception:
        return project_id


async def get_deliverable_name(deliverable_id: str):
    try:
        deliverable = await db["deliverables"].find_one({"_id": ObjectId(deliverable_id)})
        return deliverable["name"] if deliverable else deliverable_id
    except Exception:
        return deliverable_id