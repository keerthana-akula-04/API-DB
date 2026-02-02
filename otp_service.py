import random
import smtplib
from email.message import EmailMessage

# Hardcoded sender details (as requested)
SENDER_EMAIL = "keerthanaakula04@gmail.com"
SENDER_PASSWORD = "gtjwqrxwvupjeqzy"  # Gmail App Password (16 chars)

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

def send_otp_email(otp: str, role: str) -> bool:
    msg = EmailMessage()
    msg.set_content(
        f"Your verification code for {role} access is: {otp}\n\n"
        "This OTP is valid for 2 minutes."
    )
    msg["Subject"] = "Security Verification"
    msg["From"] = SENDER_EMAIL
    msg["To"] = SENDER_EMAIL  # sending to same mail (as per your setup)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print("✅ Email sent successfully")
            return True

    except Exception as e:
        print(f"❌ SMTP Error: {e}")
        return False
