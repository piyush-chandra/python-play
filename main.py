from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
import os
import shutil
from pathlib import Path
import time
import tempfile
import vercel_blob

app = FastAPI()

# Use /tmp for temporary storage if needed, but main storage is now Vercel Blob
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
    
    # Read file content
    content = await file.read()
    
    try:
        # Upload to Vercel Blob
        resp = vercel_blob.put(filename, content, options={'add_random_suffix': False})
        return {"filename": filename, "url": resp['url'], "status": "uploaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/latest")
def get_latest_file():
    try:
        # List blobs
        blobs = vercel_blob.list()
        zip_blobs = [b for b in blobs['blobs'] if b['pathname'].endswith('.zip')]
        
        if not zip_blobs:
            raise HTTPException(status_code=404, detail="No files uploaded")
        
        # Find latest blob by uploadedAt
        latest_blob = max(zip_blobs, key=lambda x: x['uploadedAt'])
        
        # Redirect to the blob URL
        return RedirectResponse(url=latest_blob['url'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve latest file: {str(e)}")

@app.post("/stream")
async def stream_file(file: UploadFile = File(...)):
    return StreamingResponse(file.file, media_type=file.content_type, headers={"Content-Disposition": f"attachment; filename={file.filename}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
