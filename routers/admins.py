from fastapi import APIRouter, Depends, HTTPException
from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/admins", tags=["Admins"])


# ---------------------------
# ROLE CHECK (SAFE + CLEAN)
# ---------------------------
def require_super_admin(user=Depends(get_current_user)):
    
    # 🔥 Normalize role (avoid case/space issues)
    role = user.get("role", "").strip().lower()

    # Optional debug (remove later)
    print("USER ROLE:", role)

    if role not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return user


# ---------------------------
# GET ADMINS
# ---------------------------
@router.get("/")
async def get_admins(user=Depends(require_super_admin)):

    cols = get_collections()

    users = await cols["clients"].find(
        {
            "role": {"$in": ["admin", "user", "pilot"]},  # includes pilot
            "status": "Active"
        },
        {
            "password": 0  # exclude password
        }
    ).to_list(100)

    # Convert ObjectId → string
    for u in users:
        u["_id"] = str(u["_id"])

    return users