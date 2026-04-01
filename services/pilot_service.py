import os
import cloudinary
import cloudinary.uploader
from sib_api_v3_sdk import Configuration, ApiClient, TransactionalEmailsApi
from sib_api_v3_sdk.models import SendSmtpEmail


# 🔹 Cloudinary Config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


async def send_pilot_email(data, files):
    try:
        uploaded_file_urls = []

        # 📤 Upload files to Cloudinary
        for file in files:
            content = await file.read()

            result = cloudinary.uploader.upload(
                content,
                resource_type="auto"
            )

            uploaded_file_urls.append(result["secure_url"])

        # 📄 Convert file URLs to HTML format
        file_links = "<br>".join(uploaded_file_urls) if uploaded_file_urls else "No files uploaded"

        # 📧 Email Content (HTML)
        html_content = f"""
        <html>
        <body>
            <p>Hello Team,</p>

            <p>A pilot has uploaded mission data. Please review the details below.</p>

            <h3>Pilot Information:</h3>
            <p>
            Name: {data['pilot_name']}<br>
            License: {data['license_number']}<br>
            Email: {data['email']}<br>
            Contact: {data['contact_number']}
            </p>

            <h3>Mission Details:</h3>
            <p>
            Date: {data['mission_date']}<br>
            Duration: {data['flight_duration']} minutes<br>
            Weather: {data['weather_conditions']}
            </p>

            <h3>Additional Comments:</h3>
            <p>{data['comments']}</p>

            <h3>Uploaded Files:</h3>
            <p>{file_links}</p>

            <br>
            <p>Regards,<br>Akin Analytics System</p>
        </body>
        </html>
        """

        # 🔹 Brevo Config
        configuration = Configuration()
        configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")

        api_instance = TransactionalEmailsApi(ApiClient(configuration))

        email = SendSmtpEmail(
            to=[{"email": os.getenv("RECEIVER_EMAIL")}],  # 👈 IMPORTANT
            sender={"email": os.getenv("SENDER_EMAIL")},
            subject=f"Pilot Mission Submission - {data['pilot_name']}",
            html_content=html_content
        )

        # 📤 Send Email (with debug)
        response = api_instance.send_transac_email(email)
        print("✅ BREVO RESPONSE:", response)

    except Exception as e:
        print("❌ BREVO ERROR:", str(e))
        raise e