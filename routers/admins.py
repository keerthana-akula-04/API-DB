from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from bson import ObjectId

from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/admins", tags=["Admins"])


@router.get("/")
async def get_admins(user=Depends(get_current_user)):

    # Only super_admin can access
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cols = get_collections()

    admins = await cols["clients"].find(
        {
            "role": {"$in": ["admin","user"]},
            "status": "Active"
        },
        {
            "password": 0
        }
    ).to_list(100)

    print("Filtered admins:", [a["role"] for a in admins])  # Debug

    return jsonable_encoder(admins, custom_encoder={ObjectId: str})
