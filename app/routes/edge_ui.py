from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/audio-file")
async def audio_file(path: str):
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="audio_not_found")
    return FileResponse(str(p), media_type="audio/mpeg")
