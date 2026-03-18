from fastapi import APIRouter, Depends, HTTPException
from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/admins", tags=["Admins"])


# Allow admin + super_admin
def require_super_admin(user=Depends(get_current_user)):
    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return user


@router.get("/")
async def get_admins(user=Depends(require_super_admin)):

    cols = get_collections()

    users = await cols["clients"].find(
        {
            "role": {"$in": ["admin", "user", "pilot"]},  # ✅ added pilot
            "status": "Active"
        },
        {
            "password": 0
        }
    ).to_list(100)

    for u in users:
        u["_id"] = str(u["_id"])

    return users