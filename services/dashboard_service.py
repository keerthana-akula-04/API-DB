from database import get_db


async def build_dashboard_response(current_user):
    db = get_db()

    # ALWAYS HIDE SUPER_ADMIN
    match_filter = {
        "status": "Active",
        "role": {"$ne": "super_admin"}  
    }

    #  ADMIN DASHBOARD COUNTS

    total_clients = await db["clients"].count_documents(match_filter)
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

    #  GLOBAL INDUSTRIES

    industries_raw = await db["industries"].find(
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
        for i in industries_raw
    ]

    #  RECENT PROJECTS

    recent_raw = await db["projects_master"].find(
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
        for p in recent_raw
    ]

    #  CLIENTS WITH ROLE FILTER

    pipeline = [
        {"$match": match_filter},  # super_admin excluded here

        {
            "$lookup": {
                "from": "projects_client",
                "localField": "_id",
                "foreignField": "client_id",
                "as": "project_links"
            }
        },

        {
            "$lookup": {
                "from": "industries",
                "localField": "project_links.industry_id",
                "foreignField": "_id",
                "as": "industry_details"
            }
        },

        {
            "$lookup": {
                "from": "projects_master",
                "localField": "project_links.project_id",
                "foreignField": "_id",
                "as": "project_details"
            }
        },

        {
            "$lookup": {
                "from": "deliverables",
                "localField": "project_links.deliverable_id",
                "foreignField": "_id",
                "as": "deliverable_details"
            }
        }
    ]

    clients_raw = await db["clients"].aggregate(pipeline).to_list(length=None)

    final_clients = []

    for client in clients_raw:

        industries_group = {}

        for link in client.get("project_links", []):

            industry = next(
                (i for i in client["industry_details"]
                 if i["_id"] == link["industry_id"]),
                None
            )

            project = next(
                (p for p in client["project_details"]
                 if p["_id"] == link["project_id"]),
                None
            )

            deliverable = next(
                (d for d in client["deliverable_details"]
                 if d["_id"] == link["deliverable_id"]),
                None
            )

            if not industry:
                continue

            industry_id = industry["_id"]

            if industry_id not in industries_group:
                industries_group[industry_id] = {
                    "id": industry.get("industry_code", ""),
                    "name": industry.get("industry_name", ""),
                    "img": industry.get("industry_image_url", ""),
                    "projects": {}
                }

            if project:
                project_id = project["_id"]

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

        # Ensure industries even if no projects
        for industry in client.get("industry_details", []):
            industry_id = industry["_id"]

            if industry_id not in industries_group:
                industries_group[industry_id] = {
                    "id": industry.get("industry_code", ""),
                    "name": industry.get("industry_name", ""),
                    "img": industry.get("industry_image_url", ""),
                    "projects": []
                }

        industries_list = []
        for ind in industries_group.values():
            if isinstance(ind["projects"], dict):
                ind["projects"] = list(ind["projects"].values())
            industries_list.append(ind)

        final_clients.append({
            "id": client.get("client_code", ""),
            "name": client.get("client_name", ""),
            "logo": client.get("logo_path", ""),
            "industries": industries_list
        })

    # FINAL RESPONSE

    return {
        "admin_dashboard": admin_dashboard,
        "clients": final_clients,
        "industries": industries,
        "recent_projects": recent_projects
    }