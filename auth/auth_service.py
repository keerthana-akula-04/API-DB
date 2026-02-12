import os
import uuid
from datetime import datetime, timedelta
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 15

if not SECRET_KEY:
    raise Exception("❌ SECRET_KEY not set")


def create_access_token(data: dict):
    return jwt.encode(
        {
            **data,
            "jti": str(uuid.uuid4()),
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def create_refresh_token(data: dict):
    return jwt.encode(
        {
            **data,
            "jti": str(uuid.uuid4()),
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )
