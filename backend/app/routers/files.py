from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.storage_service import storage

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{file_path:path}")
def serve_file(file_path: str):
    key = file_path.replace("\\", "/").lstrip("/")
    if not key or ".." in key.split("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not storage.exists(key):
        raise HTTPException(status_code=404, detail="File not found")
    data = storage.read(key)
    return Response(content=data, media_type=storage.content_type(key))
