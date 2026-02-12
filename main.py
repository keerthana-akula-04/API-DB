import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import dashboard
from database import connect_to_mongo, close_mongo_connection
from auth.auth_routes import router as auth_router

# Import routers
from routers import dashboard, reports, analytics, projects, alerts, admins

import cloudinary

app = FastAPI(title="AKIN WEB API")

load_dotenv()

# Cloudinary Config
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

# Include Routers
app.include_router(auth_router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(analytics.router)
app.include_router(projects.router)
app.include_router(alerts.router)
app.include_router(admins.router)


