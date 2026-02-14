import os
import random
import requests
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


def send_otp_email(otp: str, receiver_email: str, role: str) -> bool:
    if not BREVO_API_KEY or not SENDER_EMAIL:
        print(" Missing BREVO_API_KEY or SENDER_EMAIL")
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
        "to": [{"email": receiver_email}],
        "subject": "Security Verification Code",
        "textContent": (
            f"Your verification code for {role} access is: {otp}\n\n"
            "This OTP is valid for 5 minutes."
        )
    }

    try:
        response = requests.post(
            BREVO_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code in (200, 201, 202):
            print(" OTP sent successfully")
            return True
        else:
            print(f" Brevo error: {response.text}")
            return False

    except requests.RequestException as e:
        print(f" Email error: {e}")
        return False
