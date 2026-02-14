from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from database import get_collections
from utils.mongo_serializer import serialize_mongo
from auth.dependencies import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


# ======================================================
# HELPER FUNCTION → Find Report By Filters
# ======================================================

async def find_report_by_filters(
    cols,
    client_id,
    industry_id,
    project_id,
    deliverable_id,
    version
):
    try:
        query = {
            "client_id": client_id,
            "industry_id": ObjectId(industry_id),
            "project_id": ObjectId(project_id),
            "deliverable_id": ObjectId(deliverable_id),
            "version": version
        }
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    report = await cols["reports"].find_one(query)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return report


# ======================================================
# 1️⃣ SINGLE DYNAMIC REPORTS ENDPOINT
# ======================================================

@router.get("/")
async def get_reports(
    industry_id: str | None = None,
    project_id: str | None = None,
    deliverable_id: str | None = None,
    version: int | None = None,
    user=Depends(get_current_user)
):

    cols = get_collections()
    client_id = ObjectId(user["client_id"])

    # -------------------------------
    # MODE 1 → RETURN DROPDOWNS
    # -------------------------------
    if not industry_id and not project_id and not deliverable_id and version is None:

        base_filter = {"client_id": client_id}

        industry_ids = await cols["reports"].distinct("industry_id", base_filter)
        project_ids = await cols["reports"].distinct("project_id", base_filter)
        deliverable_ids = await cols["reports"].distinct("deliverable_id", base_filter)
        versions = await cols["reports"].distinct("version", base_filter)

        industries = await cols["industries"].find(
            {"_id": {"$in": industry_ids}}
        ).to_list(None)

        projects = await cols["projects_master"].find(
            {"_id": {"$in": project_ids}}
        ).to_list(None)

        deliverables = await cols["deliverables"].find(
            {"_id": {"$in": deliverable_ids}}
        ).to_list(None)

        return {
            "industries": [
                {"id": str(i["_id"]), "name": i["industry_name"]}
                for i in industries
            ],
            "projects": [
                {"id": str(p["_id"]), "name": p["project_name"]}
                for p in projects
            ],
            "deliverables": [
                {"id": str(d["_id"]), "name": d["deliverable_name"]}
                for d in deliverables
            ],
            "versions": sorted(versions)
        }

    # -------------------------------
    # MODE 2 → RETURN REPORT
    # -------------------------------
    if not all([industry_id, project_id, deliverable_id, version is not None]):
        raise HTTPException(
            status_code=400,
            detail="All filters are required to fetch report"
        )

    report = await find_report_by_filters(
        cols,
        client_id,
        industry_id,
        project_id,
        deliverable_id,
        version
    )

    return serialize_mongo(report)


# ======================================================
# 2️⃣ REPORT + ANALYTICS (FULL)
# ======================================================

@router.get("/analytics")
async def get_full_report(
    industry_id: str,
    project_id: str,
    deliverable_id: str,
    version: int,
    user=Depends(get_current_user)
):

    cols = get_collections()
    client_id = ObjectId(user["client_id"])

    report = await find_report_by_filters(
        cols,
        client_id,
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
