from fastapi import APIRouter, Depends
from database import get_db, get_collections
from bson import ObjectId
from datetime import datetime
from auth.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


async def build_dashboard_response(current_user):

    db = get_db()

    # -------------------------------
    # 🔹 DASHBOARD COUNTS
    # -------------------------------
    total_clients = await db["clients"].count_documents({
        "status": "Active",
        "role": "admin"
    })

    total_industries = await db["industries"].count_documents({})
    total_projects = await db["projects_client"].count_documents({})

    active_projects = await db["projects_client"].count_documents({
        "status": "Inprogress"
    })

    completed_projects = await db["projects_client"].count_documents({
        "status": "Completed"
    })

    planning_projects = await db["projects_client"].count_documents({
        "status": "Planning"
    })

    admin_dashboard = {
        "totalClients": total_clients,
        "totalIndustries": total_industries,
        "totalProjects": total_projects,
        "activeProjects": active_projects,
        "completedProjects": completed_projects,
        "planningProjects": planning_projects
    }

    # -------------------------------
    # 🔹 INDUSTRIES LIST
    # -------------------------------
    industries_raw = await db["industries"].find().to_list(None)

    industries = [
        {
            "id": i.get("industry_code"),
            "name": i.get("industry_name"),
            "img": i.get("industry_image_url")
        }
        for i in industries_raw
    ]

    # -------------------------------
    # 🔹 RECENT PROJECTS
    # -------------------------------
    recent_raw = await db["projects_master"].find(
        {"created_at": {"$exists": True}}
    ).sort("created_at", -1).limit(3).to_list(3)

    recent_projects = [
        {
            "id": p.get("project_code"),
            "name": p.get("project_name"),
            "industryId": str(p.get("industry_id")),
            "clientId": "",
            "location": p.get("location_name"),
            "img": p.get("project_image_path"),
            "date": p["created_at"].strftime("%Y-%m-%d")
            if p.get("created_at") else "",
            "status": p.get("status")
        }
        for p in recent_raw
    ]

    # -------------------------------
    # 🔥 CLIENT HIERARCHY (FIXED)
    # -------------------------------

    clients_data = await db["clients"].find(
        {"status": "Active", "role": "admin"}
    ).to_list(None)

    projects_links = await db["projects_client"].find().to_list(None)

    industries_map = {
        i["_id"]: i for i in await db["industries"].find().to_list(None)
    }

    projects_map = {
        p["_id"]: p for p in await db["projects_master"].find().to_list(None)
    }

    deliverables_map = {
        d["_id"]: d for d in await db["deliverables"].find().to_list(None)
    }

    final_clients = []

    for client in clients_data:
        client_id = client["_id"]

        # Filter projects for this client
        client_links = [
            p for p in projects_links if p["client_id"] == client_id
        ]

        industry_group = {}

        for link in client_links:

            industry = industries_map.get(link["industry_id"])
            project = projects_map.get(link["project_id"])
            deliverable = deliverables_map.get(link["deliverable_id"])

            if not industry:
                continue

            ind_key = str(industry["_id"])

            if ind_key not in industry_group:
                industry_group[ind_key] = {
                    "id": industry.get("industry_code"),
                    "name": industry.get("industry_name"),
                    "img": industry.get("industry_image_url"),
                    "projects": {}
                }

            if project:
                proj_key = str(project["_id"])

                if proj_key not in industry_group[ind_key]["projects"]:
                    industry_group[ind_key]["projects"][proj_key] = {
                        "id": project.get("project_code"),
                        "name": project.get("project_name"),
                        "location": project.get("location_name"),
                        "img": project.get("project_image_path"),
                        "status": project.get("status"),
                        "deliverables": []
                    }

                if deliverable:
                    industry_group[ind_key]["projects"][proj_key]["deliverables"].append({
                        "id": deliverable.get("deliverable_code"),
                        "name": deliverable.get("deliverable_name"),
                        "img": deliverable.get("deliverable_img_path"),
                        "date": deliverable["created_at"].strftime("%Y-%m-%d")
                        if deliverable.get("created_at") else ""
                    })

        # Convert nested dict → list
        industries_list = []

        for ind in industry_group.values():
            ind["projects"] = list(ind["projects"].values())
            industries_list.append(ind)

        final_clients.append({
            "id": client.get("client_code"),
            "name": client.get("client_name"),
            "logo": client.get("logo_path"),
            "industries": industries_list
        })

    # -------------------------------
    # FINAL RESPONSE
    # -------------------------------
    return {
        "admin_dashboard": admin_dashboard,
        "clients": final_clients,
        "industries": industries,
        "recent_projects": recent_projects
    }


# -------------------------------
# 🔹 ROUTES
# -------------------------------

@router.get("/")
async def get_dashboard(user=Depends(get_current_user)):
    return await build_dashboard_response(user)


@router.get("/notifications")
async def get_notifications(user=Depends(get_current_user)):
    cols = get_collections()

    notifications = await cols["notifications"].find().sort(
        "created_at", -1
    ).to_list(None)

    return notifications