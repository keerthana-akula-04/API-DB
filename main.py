import json
import os
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from auth.auth_routes import router as auth_router
from database import connect_to_mongo, close_mongo_connection, get_collections
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

app = FastAPI(title="API's")

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mongo lifecycle
@app.on_event("startup")
async def startup():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown():
    await close_mongo_connection()

# Routers
app.include_router(auth_router)

##UPLOAD CODE
DATA_FILE = "dataa/store.json"
os.makedirs("dataa", exist_ok=True)

# ---------------- UTIL FUNCTIONS ----------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "clients": [],
            "industries": [],
            "deliverables": [],
            "projects": [],
            "sites": [],
            "site_locations": [],
            "records": []
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def add_unique(lst, value):
    if value not in lst:
        lst.append(value)

async def upload_to_cloudinary(file: UploadFile, folder: str) -> str:
    content = await file.read()
    result = cloudinary.uploader.upload(
        content,
        folder=folder,
        resource_type="auto",
        public_id=f"{uuid.uuid4()}_{file.filename}"
    )
    return result["secure_url"]

# ================= GET API =================
@app.get("/form-data", tags=["UPLOADS"])
def get_form_data():
    data = load_data()
    return {
        "clients": data["clients"],
        "industries": data["industries"],
        "deliverables": data["deliverables"],
        "projects": data["projects"],
        "sites": data["sites"],
        "site_locations": data["site_locations"]
    }

# ================= POST API =================
@app.post("/submit-form", tags=["UPLOADS"])
async def submit_form(
    client_name: str = Form(...),
    industry: str = Form(...),
    deliverable: str = Form(...),
    project: str = Form(...),
    site_name: str = Form(...),
    site_location_map: str = Form(...),
    logo: UploadFile = File(...),
    overview: UploadFile = File(...)
):
    if not any(domain in site_location_map for domain in ["google.com", "goo.gl", "maps.app.goo.gl"]):
        raise HTTPException(status_code=400, detail="Site location must be a valid Google Maps URL")

    data = load_data()

    logo_url = await upload_to_cloudinary(logo, "project_logos")
    overview_url = await upload_to_cloudinary(overview, "project_overviews")

    add_unique(data["clients"], client_name)
    add_unique(data["industries"], industry)
    add_unique(data["deliverables"], deliverable)
    add_unique(data["projects"], project)
    add_unique(data["sites"], site_name)
    add_unique(data["site_locations"], site_location_map)

    record = {
        "client_name": client_name,
        "industry": industry,
        "deliverable": deliverable,
        "project": project,
        "site_name": site_name,
        "site_location_map": site_location_map,
        "logo_url": logo_url,
        "overview_url": overview_url
    }

    data["records"].append(record)
    save_data(data)

    cols = get_collections()

    # Store upload data
    await cols["projects_col"].database["upload"].insert_one(record)

    # 🔔 Create notification
    await cols["alerts_col"].database["notifications"].insert_one({
        "title": "New Project Uploaded",
        "message": f"Client {client_name} uploaded a new project"
    })

    return {
        "status": "success",
        "message": "Project submitted successfully",
        "logo_url": logo_url,
        "overview_url": overview_url
    }

# ================= NOTIFICATIONS =================
@app.get("/notifications", tags=["Notifications API"])
async def get_notifications():
    cols = get_collections()
    cursor = cols["alerts_col"].database["notifications"].find({}, {"_id": 0})
    return await cursor.to_list(length=None)

# ---------------- DASHBOARD ----------------
@app.get("/get-Super-Admin-Dashboard", tags=["Dashboard API's"])
async def get_super_admin_dashboard():
    cols = get_collections()
    return await cols["admin_dashboard_col"].find_one({}, {"_id": 0})

@app.get("/get-clients", tags=["Dashboard API's"])
async def get_clients():
    cols = get_collections()
    return await cols["clients_col"].find({}, {"_id": 0}).to_list(None)

@app.get("/get-industries", tags=["Dashboard API's"])
async def get_industries():
    cols = get_collections()
    return await cols["industries_col"].find({}, {"_id": 0}).to_list(None)

@app.get("/get-recent-projects", tags=["Dashboard API's"])
async def get_recent_projects():
    cols = get_collections()
    return await cols["recent_projects_col"].find({}, {"_id": 0}).to_list(None)

# ---------------- PROJECTS ----------------
@app.get("/get-projects", tags=["Projects API's"])
async def get_projects():
    cols = get_collections()
    return await cols["projects_col"].find({}, {"_id": 0}).to_list(None)

# ---------------- ANALYTICS ----------------
@app.get("/get-analytics/{project_id}", tags=["Analytical API's"])
async def get_project_analytics(project_id: str):
    cols = get_collections()
    return await cols["analytics_col"].find_one({"projectId": project_id}, {"_id": 0})

# ---------------- IMAGES ----------------
@app.get("/get-images/{project_id}", tags=["Images API's"])
async def get_images(project_id: str):
    cols = get_collections()
    return await cols["images_col"].find({"projectId": project_id}, {"_id": 0}).to_list(None)

# ---------------- ALERTS ----------------
@app.get("/get-alerts", tags=["Alerts API"])
async def get_alerts():
    cols = get_collections()
    return await cols["alerts_col"].find({}, {"_id": 0}).to_list(None)

# ---------------- MANAGEMENT ----------------
@app.get("/get-users-list", tags=["Management API's"])
async def get_users():
    cols = get_collections()
    return await cols["users_mgmt_col"].find({}, {"_id": 0}).to_list(None)

@app.get("/get-admin-list", tags=["Management API's"])
async def get_admins():
    cols = get_collections()
    admins = await cols["admin_mgmt_col"].find({}, {"_id": 0}).to_list(None)
    return [a["0"] if "0" in a else a for a in admins]
