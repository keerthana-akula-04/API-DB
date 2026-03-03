from database import get_db


async def build_dashboard_response():
    db = get_db()

    # =========================================================
    # 1️⃣ ADMIN DASHBOARD COUNTS
    # =========================================================

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

    # =========================================================
    # 2️⃣ GLOBAL INDUSTRIES (UNCHANGED)
    # =========================================================

    industries_data = await db["industries"].find(
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
        for i in industries_data
    ]

    # =========================================================
    # 3️⃣ RECENT PROJECTS (TOP 3) – UNCHANGED
    # =========================================================

    raw_projects = await db["projects_master"].find(
        {"created_at": {"$exists": True}},
        {
            "_id": 1,
            "project_code": 1,
            "project_name": 1,
            "status": 1,
            "location_name": 1,
            "industry_id": 1,
            "project_image_path": 1,
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
            "img": p.get("project_image_path", ""),
            "date": p["created_at"].strftime("%Y-%m-%d")
            if p.get("created_at") else "",
            "status": p.get("status", "")
        }
        for p in raw_projects
    ]

    # =========================================================
    # 4️⃣ CLIENTS WITH RELATED DATA ONLY
    # =========================================================

    clients_data = await db["clients"].find(
        {"status": "Active"},
        {
            "_id": 1,
            "client_code": 1,
            "client_name": 1,
            "logo_path": 1
        }
    ).to_list(length=None)

    final_clients = []

    for client in clients_data:

        client_id = client["_id"]

        # 🔹 Fetch only this client's mappings
        project_links = await db["project_clients"].find(
            {"client_id": client_id}
        ).to_list(length=None)

        if not project_links:
            continue

        industry_ids = list(set([p["industry_id"] for p in project_links]))
        project_ids = list(set([p["project_id"] for p in project_links]))
        deliverable_ids = list(set([p["deliverable_id"] for p in project_links]))

        industries_data = await db["industries"].find(
            {"_id": {"$in": industry_ids}}
        ).to_list(length=None)

        projects_data = await db["projects_master"].find(
            {"_id": {"$in": project_ids}}
        ).to_list(length=None)

        deliverables_data = await db["deliverables"].find(
            {"_id": {"$in": deliverable_ids}}
        ).to_list(length=None)

        industries_map = {i["_id"]: i for i in industries_data}
        projects_map = {p["_id"]: p for p in projects_data}
        deliverables_map = {d["_id"]: d for d in deliverables_data}

        industries_group = {}

        for link in project_links:

            industry = industries_map.get(link["industry_id"])
            project = projects_map.get(link["project_id"])
            deliverable = deliverables_map.get(link["deliverable_id"])

            if not industry or not project:
                continue

            industry_id = industry["_id"]
            project_id = project["_id"]

            if industry_id not in industries_group:
                industries_group[industry_id] = {
                    "id": industry.get("industry_code", ""),
                    "name": industry.get("industry_name", ""),
                    "img": industry.get("industry_image_url", ""),
                    "projects": {}
                }

            if project_id not in industries_group[industry_id]["projects"]:
                industries_group[industry_id]["projects"][project_id] = {
                    "id": project.get("project_code", ""),
                    "name": project.get("project_name", ""),
                    "location": project.get("location_name", ""),
                    "img": project.get("project_image_path", ""),
                    "status": project.get("status", ""),
                    "deliverables": []
                }

            if deliverable:
                industries_group[industry_id]["projects"][project_id]["deliverables"].append({
                    "id": deliverable.get("deliverable_code", ""),
                    "name": deliverable.get("deliverable_name", ""),
                    "img": deliverable.get("deliverable_img_path", ""),
                    "date": deliverable["created_at"].strftime("%Y-%m-%d")
                    if deliverable.get("created_at") else ""
                })

        # Convert dict → list
        industries_list = []
        for ind in industries_group.values():
            ind["projects"] = list(ind["projects"].values())
            industries_list.append(ind)

        final_clients.append({
            "id": client.get("client_code", ""),
            "name": client.get("client_name", ""),
            "logo": client.get("logo_path", ""),
            "industries": industries_list
        })

    # =========================================================
    # 5️⃣ FINAL RESPONSE
    # =========================================================

    return {
        "admin_dashboard": admin_dashboard,
        "clients": final_clients,
        "industries": industries,
        "recent_projects": recent_projects
    }