import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "demo_website_db"

client = None
db = None

async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )
    db = client[DATABASE_NAME]

async def close_mongo_connection():
    if client:
        client.close()

def get_collections():
    return {
        "users_auth_col": db["users"],
        "users_mgmt_col": db["users_management"],
        "admin_mgmt_col": db["admin_management"],
        "projects_col": db["projects"],
        "recent_projects_col": db["recent_projects"],
        "analytics_col": db["analytics"],
        "alerts_col": db["alerts"],
        "industries_col": db["industries"],
        "clients_col": db["clients"],
        "images_col": db["images"],
        "admin_dashboard_col": db["admin_dashboard"],
        "uploads_col": db["uploads"],
    }
