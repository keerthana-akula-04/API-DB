from fastapi import APIRouter, Depends
from database import get_collections
from auth.dependencies import get_current_user

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/")
async def get_alerts(user=Depends(get_current_user)):

    cols = get_collections()

    pipeline = [
        # Join project to get project_name
        {
            "$lookup": {
                "from": "projects_master",
                "localField": "project_id",
                "foreignField": "_id",
                "as": "project_info"
            }
        },
        {
            "$unwind": {
                "path": "$project_info",
                "preserveNullAndEmptyArrays": True
            }
        },
        # Join clients to get assigned_to name
        {
            "$lookup": {
                "from": "clients",
                "localField": "assigned_to",
                "foreignField": "_id",
                "as": "assigned_user"
            }
        },
        {
            "$unwind": {
                "path": "$assigned_user",
                "preserveNullAndEmptyArrays": True
            }
        },
        # Select only required fields
        {
            "$project": {
                "_id": 0,
                "alert_code": 1,
                "alert_details": 1,
                "project_name": "$project_info.project_name",
                "assigned_to": "$assigned_user.client_name",
                "status": 1,
                "severity": 1
            }
        }
    ]

    alerts = await cols["alerts"].aggregate(pipeline).to_list(None)

    return alerts
