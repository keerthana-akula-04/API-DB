import os
import random
import requests
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

# ✅ Fixed receiver (as you requested)
RECEIVER_EMAIL = "thrinethra098@gmail.com"

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


def send_otp_email(otp: str, role: str) -> bool:
    """
    Send OTP via Brevo API (NO SMTP)
    Always sends to thrinethra098@gmail.com
    """

    if not BREVO_API_KEY or not SENDER_EMAIL:
        print("❌ Missing BREVO_API_KEY or SENDER_EMAIL")
        return False

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    payload = {
        "sender": {
            "email": SENDER_EMAIL,
            "name": "Security Team"
        },
        "to": [
            {"email": RECEIVER_EMAIL}
        ],
        "subject": "Security Verification Code",
        "textContent": (
            f"Your verification code for {role} access is: {otp}\n\n"
            "Valid for 2 minutes."
        )
    }

    try:
        response = requests.post(BREVO_URL, json=payload, headers=headers)

        if response.status_code in (200, 201, 202):
            print("✅ OTP sent via Brevo")
            return True
        else:
            print("❌ Brevo error:", response.text)
            return False

    except Exception as e:
        print("❌ Brevo exception:", e)
        return False
