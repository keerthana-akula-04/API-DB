from fastapi import APIRouter, UploadFile, File, Form
from typing import List
from services.pilot_service import send_pilot_email

router = APIRouter()


@router.post("/pilot-data")
async def submit_pilot_data(
    # 🔹 Pilot Info
    pilot_name: str = Form(...),
    license_number: str = Form(...),
    email: str = Form(...),
    contact_number: str = Form(...),

    # 🔹 Mission Details (UPDATED FIELD NAMES)
    industry_id: str = Form(...),
    project_id: str = Form(...),
    deliverable_id: str = Form(...),
    mission_date: str = Form(...),
    flight_duration: int = Form(...),
    weather_conditions: str = Form(...),

    # 🔹 Comments
    comments: str = Form(None),

    # 🔹 Files
    files: List[UploadFile] = File(None)
):
    data = {
        "pilot_name": pilot_name,
        "license_number": license_number,
        "email": email,
        "contact_number": contact_number,

        # ✅ map frontend names → backend keys
        "industry": industry_id,
        "project": project_id,
        "deliverable": deliverable_id,

        "mission_date": mission_date,
        "flight_duration": flight_duration,
        "weather_conditions": weather_conditions,
        "comments": comments
    }

    print("📥 DATA RECEIVED:", data)

    await send_pilot_email(data, files)

    return {
        "message": "Pilot data submitted and email sent successfully"
    }