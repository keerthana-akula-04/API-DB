from database import get_db


async def build_dashboard_response():
    db = get_db()

    # =========================
    # CLIENTS (Active only)
    # =========================
    raw_clients = await db["clients"].find(
        {"status": "Active"},
        {
            "_id": 0,
            "client_name": 1,
            "logo_path": 1
        }
    ).to_list(length=None)

    clients = [
        {
            "name": c.get("client_name", ""),
            "logo": c.get("logo_path", "")
        }
        for c in raw_clients
    ]

    # =========================
    # INDUSTRIES
    # =========================
    raw_industries = await db["industries"].find(
        {},
        {
            "_id": 0,
            "industry_code": 1,
            "industry_name": 1,
            "industry_image_url": 1
        }
    ).to_list(length=None)

    industries = [
        {
            "id": i.get("industry_code", ""),
            "name": i.get("industry_name", ""),
            "img": i.get("industry_image_url", "")
        }
        for i in raw_industries
    ]

    # =========================
    # RECENT PROJECTS (TOP 3)
    # =========================
    raw_projects = await db["projects_master"].find(
        {"created_at": {"$exists": True}},
        {
            "_id": 0,
            "project_code": 1,
            "project_name": 1,
            "status": 1,
            "location_name": 1,
            "industry_id": 1,
            "project_image_path": 1,   # ✅ Added
            "created_at": 1
        }
    ).sort("created_at", -1).limit(3).to_list(length=3)

    recent_projects = [
        {
            "id": p.get("project_code", ""),
            "name": p.get("project_name", ""),
            "industryId": str(p.get("industry_id", "")),
            "clientId": "",
            "location": p.get("location_name", ""),
            "img": p.get("project_image_path", ""),  # ✅ Added
            "date": p["created_at"].strftime("%Y-%m-%d") if p.get("created_at") else "",
            "status": p.get("status", "")
        }
        for p in raw_projects
    ]

    # =========================
    # ADMIN DASHBOARD COUNTS (DYNAMIC)
    # =========================
    total_clients = await db["clients"].count_documents({"status": "Active"})
    total_industries = await db["industries"].count_documents({})
    total_projects = await db["projects_master"].count_documents({})

    active_projects = await db["projects_master"].count_documents(
        {"status": "Inprogress"}
    )

    completed_projects = await db["projects_master"].count_documents(
        {"status": "Completed"}
    )

    planning_projects = await db["projects_master"].count_documents(
        {"status": "Planning"}
    )

    admin_dashboard = {
        "totalClients": total_clients,
        "totalIndustries": total_industries,
        "totalProjects": total_projects,
        "activeProjects": active_projects,
        "completedProjects": completed_projects,
        "planningProjects": planning_projects
    }

    # =========================
    # FINAL RESPONSE
    # =========================
    return {
        "admin_dashboard": admin_dashboard,
        "clients": clients,
        "industries": industries,
        "recent_projects": recent_projects
    }
