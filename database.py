import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "demo_website_db")

client: AsyncIOMotorClient | None = None
db = None


# =========================
# Mongo Connection
# =========================
async def connect_to_mongo():
    """
    Called on FastAPI startup
    """
    global client, db

    if not MONGO_URI:
        raise Exception("❌ MONGO_URI not set in environment variables")

    client = AsyncIOMotorClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        uuidRepresentation="standard"
    )

    db = client[DATABASE_NAME]

    print("✅ MongoDB connected successfully")


async def close_mongo_connection():
    """
    Called on FastAPI shutdown
    """
    global client

    if client:
        client.close()
        print("🔴 MongoDB connection closed")


# =========================
# Helper functions
# =========================
def get_db():
    """
    Safe DB getter
    """
    if db is None:
        raise Exception("❌ Database not initialized. Did you call connect_to_mongo()?")

    return db


def get_collections():
    """
    Centralized collections access
    """
    database = get_db()

    return {
        "users_auth_col": database["users"],
        "users_mgmt_col": database["users_management"],
        "admin_mgmt_col": database["admin_management"],
        "projects_col": database["projects"],
        "recent_projects_col": database["recent_projects"],
        "analytics_col": database["analytics"],
        "alerts_col": database["alerts"],
        "industries_col": database["industries"],
        "clients_col": database["clients"],
        "images_col": database["images"],
        "admin_dashboard_col": database["admin_dashboard"],
        "uploads_col": database["uploads"],
    }
