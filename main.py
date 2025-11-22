from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import os
import shutil
from pathlib import Path
import time
import tempfile

app = FastAPI()

# Use /tmp for serverless environments (ephemeral storage)
UPLOAD_DIR = Path(tempfile.gettempdir()) / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")
    
    # Use timestamp to ensure uniqueness and order
    timestamp = int(time.time())
    filename = f"{timestamp}_{file.filename}"
    file_path = UPLOAD_DIR / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"filename": filename, "status": "uploaded"}

@app.get("/latest")
def get_latest_file():
    files = list(UPLOAD_DIR.glob("*.zip"))
    if not files:
        raise HTTPException(status_code=404, detail="No files uploaded")
    
    # Find the latest file based on modification time
    latest_file = max(files, key=os.path.getmtime)
    return FileResponse(latest_file, media_type="application/zip", filename=latest_file.name)

@app.post("/stream")
async def stream_file(file: UploadFile = File(...)):
    return StreamingResponse(file.file, media_type=file.content_type, headers={"Content-Disposition": f"attachment; filename={file.filename}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
