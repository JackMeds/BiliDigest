from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import shutil
import os
from pathlib import Path
from typing import Optional
import uvicorn
from contextlib import asynccontextmanager

# Import tools
# Note: This assumes running from project root
try:
    from tools.transcribe import transcribe_local, transcribe_openai, transcribe_gemini
    from tools.download import download_video
except ImportError:
    # If running inside tools/ dir
    import sys
    sys.path.append("..")
    from tools.transcribe import transcribe_local, transcribe_openai, transcribe_gemini

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    yield
    # Cleanup
    pass

app = FastAPI(title="Video Skill API", description="Remote interface for Video-Skill-Transcriber")

@app.post("/v1/transcribe")
async def api_transcribe(
    file: Optional[UploadFile] = File(None),
    model: str = Form("base"),
    filepath: Optional[str] = Form(None) # Local path if available
):
    """
    Transcribe an uploaded file or a local file path.
    Models: 'base', 'large-v3', 'openai', 'gemini'
    """
    target_path = None
    
    # 1. Handle File Source
    if file:
        target_path = Path(f"uploads/{file.filename}")
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    elif filepath:
        target_path = Path(filepath)
        if not target_path.exists():
            raise HTTPException(404, "File path not found")
    else:
        raise HTTPException(400, "Must provide 'file' or 'filepath'")

    # 2. Select Model
    print(f"📡 API Request: Transcribe {target_path} using {model}")
    
    result_text = None
    try:
        model_lower = model.lower()
        if "gemini" in model_lower:
            result_text = transcribe_gemini(target_path)
        elif model_lower in ["openai", "whisper-1"]:
            result_text = transcribe_openai(target_path, "whisper-1")
        else:
            # Local
            result_text = transcribe_local(target_path, model, "auto")
            
        if not result_text:
            raise HTTPException(500, "Transcription failed (returned empty)")
            
        return {
            "status": "success",
            "model": model,
            "text": result_text
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
