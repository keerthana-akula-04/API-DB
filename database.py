import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "akin_platform_db")

client = None
db = None


async def connect_to_mongo():
    global client, db

    if not MONGO_URI:
        raise Exception("MONGO_URI not set")

    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DATABASE_NAME]

    print("✅ MongoDB connected")


async def close_mongo_connection():
    global client

    if client:
        client.close()
        print("❌ MongoDB disconnected")


def get_db():
    if db is None:
        raise Exception("DB not initialized")

    return db


def get_collections():
    db_instance = get_db()

    return {
        "pilot": db_instance["Pilot"],  # ✅ important
        "clients": db_instance["clients"],
        "industries": db_instance["industries"],
        "projects_master": db_instance["projects_master"],
        "projects_client": db_instance["projects_client"],
        "reports": db_instance["reports"],
        "analytics": db_instance["analytics"],
        "alerts": db_instance["alerts"],
        "notifications": db_instance["notifications"],
        "dashboard": db_instance["dashboard"],
        "deliverables": db_instance["deliverables"],
        "sessions_col": db_instance["sessions"]
    }