from database import get_db
from bson import ObjectId


async def build_dashboard_response(client_id: str = None):
    db = get_db()

    # ==========================================================
    # CLIENTS (Always from clients collection)
    # ==========================================================

    raw_clients = await db["clients"].find(
        {"status": "Active"},
        {
            "_id": 1,
            "client_code": 1,
            "client_name": 1,
            "logo_path": 1
        }
    ).to_list(length=None)

    clients = [
        {
            "id": c["client_code"],
            "name": c["client_name"],
            "logo": c.get("logo_path", "")
        }
        for c in raw_clients
    ]

    # ==========================================================
    # FILTER (if client_id passed)
    # ==========================================================

    dashboard_filter = {}

    if client_id:
        dashboard_filter["client_id"] = ObjectId(client_id)

    # ==========================================================
    # INDUSTRIES (Unique)
    # ==========================================================

    pipeline = [
        {"$match": dashboard_filter},

        {
            "$group": {
                "_id": "$industry_id"
            }
        },

        {
            "$lookup": {
                "from": "industries",
                "localField": "_id",
                "foreignField": "_id",
                "as": "industry"
            }
        },
        {"$unwind": "$industry"},

        {
            "$project": {
                "_id": 0,
                "id": "$industry.industry_code",
                "name": "$industry.industry_name",
                "img": "$industry.industry_image_url"
            }
        }
    ]

    industries = await db["dashboard"].aggregate(pipeline).to_list(length=None)

    # ==========================================================
    # RECENT PROJECTS (Top 3)
    # ==========================================================

    recent_projects_pipeline = [
        {"$match": dashboard_filter},

        {"$sort": {"created_at": -1}},

        {
            "$group": {
                "_id": "$project_id",
                "name": {"$first": "$project_name"},
                "industryId": {"$first": "$industry_id"},
                "clientId": {"$first": "$client_id"},
                "location": {"$first": "$location"},
                "img": {"$first": "$project_url"},
                "date": {"$first": "$created_at"},
                "status": {"$first": "$status"}
            }
        },

        {"$limit": 3}
    ]

    raw_recent = await db["dashboard"].aggregate(recent_projects_pipeline).to_list(length=3)

    recent_projects = [
        {
            "id": str(p["_id"]),
            "name": p["name"],
            "industryId": str(p["industryId"]),
            "clientId": str(p["clientId"]),
            "location": p["location"],
            "img": p["img"],
            "date": p["date"].strftime("%Y-%m-%d") if p.get("date") else "",
            "status": p["status"]
        }
        for p in raw_recent
    ]

    # ==========================================================
    # ADMIN DASHBOARD COUNTS
    # ==========================================================

    total_clients = await db["clients"].count_documents({"status": "Active"})
    total_industries = await db["industries"].count_documents({})
    total_projects = await db["dashboard"].count_documents({})

    active_projects = await db["dashboard"].count_documents({"status": "Inprogress"})
    completed_projects = await db["dashboard"].count_documents({"status": "Completed"})
    planning_projects = await db["dashboard"].count_documents({"status": "Planning"})

    admin_dashboard = {
        "totalClients": total_clients,
        "totalIndustries": total_industries,
        "totalProjects": total_projects,
        "activeProjects": active_projects,
        "completedProjects": completed_projects,
        "planningProjects": planning_projects
    }

    # ==========================================================
    # FINAL RESPONSE
    # ==========================================================

    return {
        "admin_dashboard": admin_dashboard,
        "clients": clients,
        "industries": industries,
        "recent_projects": recent_projects
    }