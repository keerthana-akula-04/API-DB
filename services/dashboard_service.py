from database import get_db


async def build_dashboard_response():
    db = get_db()

    # ==============================
    # ADMIN DASHBOARD COUNTS
    # ==============================
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
        "planningProjects": planning_projects,
    }

    # ==============================
    # CLIENTS WITH RELATED DATA
    # ==============================
    raw_clients = await db["clients"].find(
        {"status": "Active"}
    ).to_list(None)

    clients_response = []

    for client in raw_clients:

        # Get mapping records for this client
        mappings = await db["project_client"].find(
            {"client_id": client["_id"]}
        ).to_list(None)

        industry_map = {}

        for map_item in mappings:

            # ---------------------------
            # INDUSTRY
            # ---------------------------
            industry = await db["industries"].find_one(
                {"_id": map_item["industry_id"]}
            )

            if not industry:
                continue

            industry_code = industry["industry_code"]

            if industry_code not in industry_map:
                industry_map[industry_code] = {
                    "id": industry["industry_code"],
                    "name": industry["industry_name"],
                    "img": industry.get("industry_image_url", ""),
                    "projects": {}
                }

            # ---------------------------
            # PROJECT
            # ---------------------------
            project = await db["projects_master"].find_one(
                {"_id": map_item["project_id"]}
            )

            if not project:
                continue

            project_code = project["project_code"]

            if project_code not in industry_map[industry_code]["projects"]:
                industry_map[industry_code]["projects"][project_code] = {
                    "id": project["project_code"],
                    "name": project["project_name"],
                    "status": project.get("status", ""),
                    "location": project.get("location_name", ""),
                    "progress": map_item.get("progress", 0),
                    "img": project.get("project_image_path", ""),
                    "deliverables": []
                }

            # ---------------------------
            # DELIVERABLE
            # ---------------------------
            deliverable = await db["deliverables"].find_one(
                {"_id": map_item["deliverable_id"]}
            )

            if deliverable:
                industry_map[industry_code]["projects"][project_code]["deliverables"].append({
                    "id": deliverable.get("deliverable_code", ""),
                    "name": deliverable.get("deliverable_name", ""),
                    "img": deliverable.get("deliverable_img_path", "")
                })

        # Convert nested project dict to list
        industries_list = []

        for industry in industry_map.values():
            industry["projects"] = list(industry["projects"].values())
            industries_list.append(industry)

        clients_response.append({
            "id": client.get("client_code", ""),
            "name": client.get("client_name", ""),
            "logo": client.get("logo_path", ""),
            "industries": industries_list
        })

    # ==============================
    # RECENT PROJECTS (LATEST 3)
    # ==============================
    raw_recent_projects = await db["projects_master"].find(
        {"created_at": {"$exists": True}}
    ).sort("created_at", -1).limit(3).to_list(3)

    recent_projects = [
        {
            "id": p.get("project_code", ""),
            "name": p.get("project_name", ""),
            "status": p.get("status", ""),
            "date": p["created_at"].strftime("%Y-%m-%d")
            if p.get("created_at") else "",
        }
        for p in raw_recent_projects
    ]

    # ==============================
    # FINAL RESPONSE
    # ==============================
    return {
        "admin_dashboard": admin_dashboard,
        "clients": clients_response,
        "recent_projects": recent_projects
    }