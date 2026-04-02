from fastapi import APIRouter, UploadFile, File
import shutil
import tempfile

router = APIRouter()
@router.post("/api/audio/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")

    with open(temp.name, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print(f"[AUDIO RECEBIDO]: {temp.name}")

    # mock temporário até ligar Whisper/OpenAI
    return {"text": "olá, como posso te ajudar?"}
