from fastapi import APIRouter, Depends, HTTPException
from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/admins", tags=["Admins"])


# Allow ONLY super_admin
def require_super_admin(user=Depends(get_current_user)):
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return user


@router.get("/")
async def get_admins(user=Depends(require_super_admin)):

    cols = get_collections()

    # Fetch admin + user roles only
    users = await cols["clients"].find(
        {
            "role": {"$in": ["admin", "user"]},
            "status": "Active"
        },
        {
            "password": 0  # Exclude password
        }
    ).to_list(100)

    # Convert ObjectId to string
    for u in users:
        u["_id"] = str(u["_id"])

    return users
