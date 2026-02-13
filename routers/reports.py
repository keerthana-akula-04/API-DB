from fastapi import APIRouter, Depends, Query, HTTPException
from bson import ObjectId
from database import get_collections
from utils.mongo_serializer import serialize_mongo
from auth.dependencies import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


# ==========================================
# SINGLE DYNAMIC REPORTS ENDPOINT
# ==========================================
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

    # ------------------------------------------------
    # CASE 1 → NO FILTERS → RETURN DROPDOWNS
    # ------------------------------------------------
    if not industry_id and not project_id and not deliverable_id and not version:

        industry_ids = await cols["reports"].distinct("industry_id", {"client_id": client_id})
        project_ids = await cols["reports"].distinct("project_id", {"client_id": client_id})
        deliverable_ids = await cols["reports"].distinct("deliverable_id", {"client_id": client_id})
        versions = await cols["reports"].distinct("version", {"client_id": client_id})

        industries_data = await cols["industries"].find(
            {"_id": {"$in": industry_ids}}
        ).to_list(None)

        projects_data = await cols["projects_master"].find(
            {"_id": {"$in": project_ids}}
        ).to_list(None)

        deliverables_data = await cols["deliverables"].find(
            {"_id": {"$in": deliverable_ids}}
        ).to_list(None)

        return {
            "industries": [
                {"id": str(i["_id"]), "name": i["industry_name"]}
                for i in industries_data
            ],
            "projects": [
                {"id": str(p["_id"]), "name": p["project_name"]}
                for p in projects_data
            ],
            "deliverables": [
                {"id": str(d["_id"]), "name": d["deliverable_name"]}
                for d in deliverables_data
            ],
            "versions": versions
        }

    # ------------------------------------------------
    # CASE 2 → FILTERS PROVIDED → RETURN REPORT
    # ------------------------------------------------
    query = {"client_id": client_id}

    if industry_id:
        query["industry_id"] = ObjectId(industry_id)
    if project_id:
        query["project_id"] = ObjectId(project_id)
    if deliverable_id:
        query["deliverable_id"] = ObjectId(deliverable_id)
    if version:
        query["version"] = version

    reports = await cols["reports"].find(query).to_list(None)

    if not reports:
        raise HTTPException(status_code=404, detail="Report not found")

    return serialize_mongo(reports)


# ==========================================
# UNIFIED REPORT + ANALYTICS ENDPOINT
# ==========================================
@router.get("/full")
async def get_full_report(
    industry_id: str,
    project_id: str,
    deliverable_id: str,
    version: int,
    user=Depends(get_current_user)
):

    cols = get_collections()
    client_id = ObjectId(user["client_id"])

    report = await cols["reports"].find_one({
        "client_id": client_id,
        "industry_id": ObjectId(industry_id),
        "project_id": ObjectId(project_id),
        "deliverable_id": ObjectId(deliverable_id),
        "version": version
    })

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    analytics = await cols["analytics"].find_one({
        "report_id": report["_id"]
    })

    return {
        "report": serialize_mongo(report),
        "analytics": serialize_mongo(analytics) if analytics else None
    }
