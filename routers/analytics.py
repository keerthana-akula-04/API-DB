from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from database import get_collections
from utils.mongo_serializer import serialize_mongo
from auth.dependencies import get_current_user
from routers.reports import find_report_by_filters

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ======================================================
# SINGLE DYNAMIC ANALYTICS ENDPOINT (CASCADING)
# ======================================================

@router.get("/")
async def get_analytics(
    industry_id: str | None = None,
    project_id: str | None = None,
    deliverable_id: str | None = None,
    version: int | None = None,
    user=Depends(get_current_user)
):
    cols = get_collections()

    # ======================================================
    # STEP 1 → NO FILTER → RETURN INDUSTRIES
    # ======================================================
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

    # ======================================================
    # STEP 2 → INDUSTRY SELECTED → RETURN PROJECTS
    # ======================================================
    if industry_id and not project_id:

        try:
            industry_obj = ObjectId(industry_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid industry_id")

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

    # ======================================================
    # STEP 3 → PROJECT SELECTED → RETURN DELIVERABLES
    # ======================================================
    if industry_id and project_id and not deliverable_id:

        try:
            project_obj = ObjectId(project_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid project_id")

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

    # ======================================================
    # STEP 4 → DELIVERABLE SELECTED → RETURN VERSIONS
    # ======================================================
    if industry_id and project_id and deliverable_id and version is None:

        try:
            industry_obj = ObjectId(industry_id)
            project_obj = ObjectId(project_id)
            deliverable_obj = ObjectId(deliverable_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid ID format")

        version_filter = {
            "industry_id": industry_obj,
            "project_id": project_obj,
            "deliverable_id": deliverable_obj
        }

        # 🔥 Role based filtering
        if user["role"] != "super_admin":
            version_filter["client_id"] = ObjectId(user["client_id"])

        versions = await cols["reports"].distinct("version", version_filter)

        return {
            "versions": sorted(versions)
        }

    # ======================================================
    # STEP 5 → ALL SELECTED → RETURN FINAL ANALYTICS
    # ======================================================
    if industry_id and project_id and deliverable_id and version is not None:

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

    raise HTTPException(status_code=400, detail="Invalid request parameters")
