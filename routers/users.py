from fastapi import APIRouter, Depends, HTTPException
from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


# 🔐 Role check (same as admin API)
def require_super_admin(user=Depends(get_current_user)):
    if user.get("role") not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return user


# 📥 GET Users + Pilots
@router.get("/")
async def get_users(user=Depends(require_super_admin)):

    cols = get_collections()

    users = await cols["clients"].find(
        {
            "role": {"$in": ["user", "pilot"]},   # ✅ only user & pilot
            "status": "Active"
        },
        {
            "password": 0   # 🔒 exclude password
        }
    ).to_list(100)

    # 🔄 Convert ObjectId → string
    for u in users:
        u["_id"] = str(u["_id"])

    return users