from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from database import get_collections
from auth.dependencies import get_current_user
from utils.security import hash_password 

router = APIRouter(prefix="/users", tags=["Users"])


class UserRegisterRequest(BaseModel):
    client_name: str | None = Field(default=None, alias="Client Name")
    user_name: str = Field(..., alias="User Name")
    email_id: EmailStr = Field(..., alias="Email")
    password: str

    class Config:
        populate_by_name = True  


