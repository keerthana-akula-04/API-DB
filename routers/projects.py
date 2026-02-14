from fastapi import APIRouter, Depends
from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/")
async def get_projects(user=Depends(get_current_user)):

    cols = get_collections()

    pipeline = [
        {
            "$lookup": {
                "from": "industries",
                "localField": "industry_id",
                "foreignField": "_id",
                "as": "industry_info"
            }
        },
        {
            "$unwind": {
                "path": "$industry_info",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$project": {
                "_id": 0,
                "project_code": 1,
                "project_name": 1,
                "industry_name": "$industry_info.industry_name",
                "location_name": 1,
                "status": 1,

                # ✅ Formatted Dates
                "created_at": {
                    "$dateToString": {
                        "format": "%d-%m-%Y %H:%M",
                        "date": "$created_at"
                    }
                },
                "updated_at": {
                    "$dateToString": {
                        "format": "%d-%m-%Y %H:%M",
                        "date": "$updated_at"
                    }
                }
            }
        }
    ]

    projects = await cols["projects_master"].aggregate(pipeline).to_list(None)

    return projects
