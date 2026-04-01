import os
import cloudinary
import cloudinary.uploader
from sib_api_v3_sdk import Configuration, ApiClient, TransactionalEmailsApi
from sib_api_v3_sdk.models import SendSmtpEmail

from services.db_lookup import (
    get_industry_name,
    get_project_name,
    get_deliverable_name
)


# 🔹 Cloudinary Config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


async def send_pilot_email(data, files):
    try:
        uploaded_file_urls = []

        # 📤 Upload files safely
        if files:
            for file in files:
                content = await file.read()

                result = cloudinary.uploader.upload(
                    content,
                    resource_type="auto"
                )

                uploaded_file_urls.append(result["secure_url"])

        # 📄 File links
        file_links = "\n".join(uploaded_file_urls) if uploaded_file_urls else "No files uploaded"

        # 🔹 Convert IDs → Names
        industry = await get_industry_name(data["industry"])
        project = await get_project_name(data["project"])
        deliverable = await get_deliverable_name(data["deliverable"])

        # 📧 Email Content (PLAIN TEXT)
        text_content = f"""
Hello Team,

A pilot has uploaded mission data. Please review the details below.

-------------------------------
Pilot Information:
-------------------------------
Name: {data['pilot_name']}
License: {data['license_number']}
Email: {data['email']}
Contact: {data['contact_number']}

-------------------------------
Mission Details:
-------------------------------
Industry: {industry}
Project: {project}
Deliverable: {deliverable}
Date: {data['mission_date']}
Duration: {data['flight_duration']} minutes
Weather: {data['weather_conditions']}

-------------------------------
Additional Comments:
-------------------------------
{data['comments']}

-------------------------------
Uploaded Files:
-------------------------------
{file_links}

Regards,
Akin Analytics Solutions
"""

        # 🔹 Brevo Config
        configuration = Configuration()
        configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")

        api_instance = TransactionalEmailsApi(ApiClient(configuration))

        email = SendSmtpEmail(
            to=[{"email": os.getenv("RECEIVER_EMAIL")}],
            sender={"email": os.getenv("SENDER_EMAIL")},
            subject=f"Pilot Mission Submission - {data['pilot_name']}",
            text_content=text_content
        )

        response = api_instance.send_transac_email(email)
        print("✅ BREVO RESPONSE:", response)

    except Exception as e:
        print("❌ BREVO ERROR:", str(e))
        raise e