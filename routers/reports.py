from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from database import get_collections
from utils.mongo_serializer import serialize_mongo
from auth.dependencies import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


# HELPERS

def to_object_id(id_str: str, field_name: str):
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}")


#  NO ROLE FILTER 
def apply_role_filter(query: dict, user: dict):
    return query


async def find_report_by_filters(
    cols,
    user,
    industry_id,
    project_id,
    deliverable_id,
    version
):
    query = {
        "industry_id": to_object_id(industry_id, "industry_id"),
        "project_id": to_object_id(project_id, "project_id"),
        "deliverable_id": to_object_id(deliverable_id, "deliverable_id"),
        "version": version
    }

    #  No restriction applied
    query = apply_role_filter(query, user)

    report = await cols["reports"].find_one(query)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return report


@router.get("/")
async def get_reports(
    industry_id: str | None = None,
    project_id: str | None = None,
    deliverable_id: str | None = None,
    version: int | None = None,
    user=Depends(get_current_user)
):
    cols = get_collections()

    if not industry_id:
        industries = await cols["industries"].find(
            {},
            {"_id": 1, "industry_name": 1}
        ).to_list(None)

        return {
            "industries": [
                {"id": str(i["_id"]), "name": i["industry_name"]}
                for i in industries
            ]
        }

    if industry_id and not project_id:
        industry_obj = to_object_id(industry_id, "industry_id")

        projects = await cols["projects_master"].find(
            {"industry_id": industry_obj},
            {"_id": 1, "project_name": 1}
        ).to_list(None)

        return {
            "projects": [
                {"id": str(p["_id"]), "name": p["project_name"]}
                for p in projects
            ]
        }

    if industry_id and project_id and not deliverable_id:
        project_obj = to_object_id(project_id, "project_id")

        deliverables = await cols["deliverables"].find(
            {"project_id": project_obj},
            {"_id": 1, "deliverable_name": 1}
        ).to_list(None)

        return {
            "deliverables": [
                {"id": str(d["_id"]), "name": d["deliverable_name"]}
                for d in deliverables
            ]
        }

    if industry_id and project_id and deliverable_id and version is None:

        version_filter = {
            "industry_id": to_object_id(industry_id, "industry_id"),
            "project_id": to_object_id(project_id, "project_id"),
            "deliverable_id": to_object_id(deliverable_id, "deliverable_id"),
            "version": {"$ne": None}
        }

        version_filter = apply_role_filter(version_filter, user)

        versions = await cols["reports"].distinct("version", version_filter)

        versions = [v for v in versions if v is not None]

        return {
            "versions": sorted(versions) if versions else []
        }

    if industry_id and project_id and deliverable_id and version is not None:

        report = await find_report_by_filters(
            cols,
            user,
            industry_id,
            project_id,
            deliverable_id,
            version
        )

        return serialize_mongo(report)

    raise HTTPException(status_code=400, detail="Invalid request parameters")



@router.get("/analytics")
async def get_full_report(
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

    return {
        "report": serialize_mongo(report),
        "analytics": serialize_mongo(analytics) if analytics else None
    }