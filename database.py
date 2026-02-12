import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "akin_platform_db")

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
    db_instance = get_db()  # ✅ Always get DB safely

    return {
        "clients": db_instance["clients"],
        "industries": db_instance["industries"],
        "projects_master": db_instance["projects_master"],
        "projects_client": db_instance["projects_client"],
        "reports": db_instance["reports"],
        "analytics": db_instance["analytics"],
        "alerts": db_instance["alerts"],
        "notifications": db_instance["notifications"],  # ✅ FIXED
        "dashboard": db_instance["dashboard"],
        "deliverables": db_instance["deliverables"],
        "sessions_col": db_instance["sessions"]
    }
