from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth.auth_routes import router as auth_router
from database import connect_to_mongo, close_mongo_connection, get_collections
from upload_routes import router as upload_router


app = FastAPI(title="API's")

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
app.include_router(upload_router)

# ---------------- DASHBOARD ----------------
@app.get("/get-Super-Admin-Dashboard", tags=["Dashboard API's"])
async def get_super_admin_dashboard():
    cols = get_collections()
    return await cols["admin_dashboard_col"].find_one({}, {"_id": 0})

@app.get("/get-clients", tags=["Dashboard API's"])
async def get_clients():
    cols = get_collections()
    cursor = cols["clients_col"].find({}, {"_id": 0})
    return await cursor.to_list(length=None)

@app.get("/get-industries", tags=["Dashboard API's"])
async def get_industries():
    cols = get_collections()
    cursor = cols["industries_col"].find({}, {"_id": 0})
    return await cursor.to_list(length=None)

@app.get("/get-recent-projects", tags=["Dashboard API's"])
async def get_recent_projects():
    cols = get_collections()
    cursor = cols["recent_projects_col"].find({}, {"_id": 0})
    return await cursor.to_list(length=None)

# ---------------- PROJECTS ----------------
@app.get("/get-projects", tags=["Projects API's"])
async def get_projects():
    cols = get_collections()
    cursor = cols["projects_col"].find({}, {"_id": 0})
    return await cursor.to_list(length=None)

# ---------------- ANALYTICS ----------------
@app.get("/get-analytics/{project_id}", tags=["Analytical API's"])
async def get_project_analytics(project_id: str):
    cols = get_collections()
    data = await cols["analytics_col"].find_one(
        {"projectId": project_id},
        {"_id": 0}
    )
    return data if data else {"error": "Analytics not found"}

# ---------------- IMAGES ----------------
@app.get("/get-images/{project_id}", tags=["Images API's"])
async def get_images(project_id: str):
    cols = get_collections()
    cursor = cols["images_col"].find(
        {"projectId": project_id},
        {"_id": 0}
    )
    return await cursor.to_list(length=None)

# ---------------- ALERTS ----------------
@app.get("/get-alerts", tags=["Alerts API"])
async def get_alerts():
    cols = get_collections()
    cursor = cols["alerts_col"].find({}, {"_id": 0})
    return await cursor.to_list(length=None)

# ---------------- MANAGEMENT ----------------
@app.get("/get-users-list", tags=["Management API's"])
async def get_users():
    cols = get_collections()
    cursor = cols["users_mgmt_col"].find({}, {"_id": 0})
    return await cursor.to_list(length=None)

@app.get("/get-admin-list", tags=["Management API's"])
async def get_admins():
    cols = get_collections()
    cursor = cols["admin_mgmt_col"].find({}, {"_id": 0})
    admins = await cursor.to_list(length=None)
    return [a["0"] if "0" in a else a for a in admins]
