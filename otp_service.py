import os
import random
import requests
from dotenv import load_dotenv

load_dotenv()
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

# ✅ Fixed receiver (always send here)
RECEIVER_EMAIL = "thrinethra098@gmail.com"

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


# ================= OTP =================
def generate_otp() -> str:
    return str(random.randint(100000, 999999))


# ================= SEND EMAIL =================
def send_otp_email(otp: str, role: str) -> bool:
    """
    Send OTP using Brevo REST API (NO SMTP)
    Always sends to fixed receiver
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
        "to": [{"email": RECEIVER_EMAIL}],
        "subject": "Security Verification Code",
        "textContent": (
            f"Your verification code for {role} access is: {otp}\n\n"
            "Valid for 2 minutes."
        )
    }

    try:
        response = requests.post(
            BREVO_URL,
            json=payload,
            headers=headers,
            timeout=10  # ✅ important for production
        )

        if response.status_code in (200, 201, 202):
            print("✅ OTP sent via Brevo successfully")
            return True

        print(f"❌ Brevo failed: {response.text}")
        return False

    except requests.RequestException as e:
        print(f"❌ Brevo request error: {e}")
        return False
