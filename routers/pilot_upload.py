from fastapi import APIRouter, UploadFile, File, Form, Query
from typing import List
from datetime import datetime
from database import get_collections
from bson import ObjectId
import cloudinary.uploader

router = APIRouter(tags=["Pilot-API's"])


# =========================================================
# ✅ 1. GET API (Dropdown + Autofill)
# =========================================================
@router.get("/pilot-data")
async def get_pilot_data(client_id: str = Query(None)):
    try:
        collections = get_collections()

        clients_col = collections["clients"]
        project_client_col = collections["projects_client"]
        industries_col = collections["industries"]
        projects_master_col = collections["projects_master"]
        deliverables_col = collections["deliverables"]

        # 🔹 Dropdown (ONLY pilot_name)
        pilots = []
        async for doc in clients_col.find({}, {"_id": 1, "pilot_name": 1}):
            name = doc.get("pilot_name")
            if not name:
                continue

            pilots.append({
                "label": name,
                "value": str(doc.get("_id"))
            })

        # 🔹 Only dropdown
        if not client_id:
            return {
                "status": True,
                "pilots": pilots
            }

        # 🔹 Convert ID
        try:
            client_obj_id = ObjectId(client_id)
        except:
            return {"status": False, "message": "Invalid client_id format"}

        # 🔹 Get client
        client = await clients_col.find_one({"_id": client_obj_id})
        if not client:
            return {"status": False, "message": "Client not found"}

        # 🔹 Handle ObjectId + string mismatch
        project_data = await project_client_col.find_one({
            "$or": [
                {"client_id": client_obj_id},
                {"client_id": client_id}
            ]
        })

        # 🔥 If no mapping → still return pilot data
        if not project_data:
            return {
                "status": True,
                "pilots": pilots,
                "data": {
                    "pilot_name": client.get("pilot_name"),
                    "license_number": client.get("license_number"),
                    "email": client.get("email_id"),
                    "contact_number": client.get("contact_number"),

                    "industry_name": None,
                    "project_name": None,
                    "deliverable_name": None,

                    "weather_conditions": [
                        "Sunny", "Cloudy", "Partly Cloudy",
                        "Rainy", "Windy", "Stormy", "Foggy"
                    ]
                },
                "message": "No project mapping found for this pilot"
            }

        # 🔹 Fetch related data
        industry = await industries_col.find_one({
            "_id": ObjectId(project_data["industry_id"])
        })

        project = await projects_master_col.find_one({
            "_id": ObjectId(project_data["project_id"])
        })

        deliverable = await deliverables_col.find_one({
            "_id": ObjectId(project_data["deliverable_id"])
        })

        return {
            "status": True,
            "pilots": pilots,
            "data": {
                "pilot_name": client.get("pilot_name"),
                "license_number": client.get("license_number"),
                "email": client.get("email_id"),
                "contact_number": client.get("contact_number"),

                "industry_name": industry.get("industry_name") if industry else None,
                "project_name": project.get("project_name") if project else project_data.get("project_name"),
                "deliverable_name": deliverable.get("deliverable_name") if deliverable else None,

                "weather_conditions": [
                    "Sunny", "Cloudy", "Partly Cloudy",
                    "Rainy", "Windy", "Stormy", "Foggy"
                ]
            }
        }

    except Exception as e:
        return {
            "status": False,
            "message": "Error",
            "error": str(e)
        }


# =========================================================
# ✅ 2. POST API (Save Data)
# =========================================================
@router.post("/pilot-upload")
async def submit_pilot_data(
    client_id: str = Form(...),

    industry_id: str = Form(...),
    project_id: str = Form(...),
    deliverable_id: str = Form(...),

    mission_date: str = Form(...),
    flight_duration_minutes: int = Form(...),
    weather_conditions: str = Form(...),

    data_url: str = Form(...),
    additional_comments: str = Form(None),

    files: List[UploadFile] = File(None)
):
    try:
        collections = get_collections()

        pilot_collection = collections["pilot"]
        clients_col = collections["clients"]

        client_obj_id = ObjectId(client_id)

        # 🔹 Get client
        client = await clients_col.find_one({"_id": client_obj_id})
        if not client:
            return {"status": False, "message": "Client not found"}

        # 🔹 Convert date
        mission_date_obj = datetime.strptime(mission_date, "%d/%m/%Y")

        # 🔹 Upload files
        file_urls = []
        if files:
            for file in files:
                result = cloudinary.uploader.upload(file.file)
                file_urls.append(result["secure_url"])

        # 🔹 Final DB format
        data = {
            "Pilot_name": client.get("pilot_name"),
            "License_number": client.get("license_number"),
            "Email": client.get("email_id"),
            "Contact_number": client.get("contact_number"),

            "Client_ID": client_id,
            "Industry_ID": industry_id,
            "Project_ID": project_id,
            "Deliverable_ID": deliverable_id,

            "Mission_Date": mission_date_obj,
            "Flight_Duration": str(flight_duration_minutes),
            "Weather_conditions": weather_conditions,

            "Data_Url": file_urls[0] if file_urls else data_url,
            "Files": file_urls,

            "Additional_notes": additional_comments,
            "Created_at": datetime.utcnow()
        }

        result = await pilot_collection.insert_one(data)

        return {
            "status": True,
            "message": "Pilot data saved successfully",
            "id": str(result.inserted_id)
        }

    except Exception as e:
        return {
            "status": False,
            "message": "Failed to save",
            "error": str(e)
        }