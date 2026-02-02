import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from database import get_collections

router = APIRouter(prefix="/upload", tags=["Upload API"])

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- POST: UPLOAD FILE ----------------
@router.post("/file")
async def upload_file(file: UploadFile = File(...)):
    cols = get_collections()
    uploads_col = cols["uploads_col"]

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception:
        raise HTTPException(status_code=500, detail="File upload failed")

    data = {
        "file_id": file_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "file_path": file_path
    }

    await uploads_col.insert_one(data)

    return {
        "message": "File uploaded successfully",
        "file_id": file_id,
        "filename": file.filename
    }

# ---------------- GET: FETCH UPLOADED FILES ----------------
@router.get("/get-upload")
async def get_uploaded_files():
    cols = get_collections()
    uploads_col = cols["uploads_col"]

    cursor = uploads_col.find({}, {"_id": 0})
    return await cursor.to_list(length=None)
