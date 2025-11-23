from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import tempfile
from dotenv import load_dotenv
import time
import os
import uvicorn
import vercel_blob
import requests
import base64

load_dotenv()

token = os.getenv("BLOB_READ_WRITE_TOKEN")
print(f"Token loaded: {'Yes' if token else 'No'}")
if token:
    print(f"Token prefix: {token[:5]}...")

app = FastAPI()

UPLOAD_DIR = Path(tempfile.gettempdir()) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 1024 * 1024  # 1 MB


@app.get("/")
def read_root():
    return {"message": "FastAPI file streamer is up"}


@app.get("/health")
def health_check():
    return {"status": "ok"}

# check text post working or not
class TestPayload(BaseModel):
    data: str
    chunkNumber: int
    totalChunks: int
    fileName: str
    isCompleted: bool
    isStarted: bool

# this is for client side testing
@app.post("/test1")
def testText(payload: TestPayload):
    safe_filename = Path(payload.fileName).name
    temp_file_path = UPLOAD_DIR / f"temp_{safe_filename}"
    
    try:
        chunk_data = b""
        if payload.data:
            chunk_data = base64.b64decode(payload.data)
            
        if payload.isStarted:
            with open(temp_file_path, "wb") as f:
                f.write(chunk_data)
            return {"status": "started", "message": "File initialized"}
        
        elif payload.isCompleted:
            if chunk_data:
                with open(temp_file_path, "ab") as f:
                    f.write(chunk_data)
            
            if not temp_file_path.exists():
                 raise HTTPException(status_code=400, detail="Upload session not found (file missing)")
                 
            with open(temp_file_path, "rb") as f:
                content = f.read()
            
            try:
                list_resp = vercel_blob.list()
                existing_blobs = list_resp.get("blobs", [])
                for b in existing_blobs:
                    if b["pathname"].endswith(f"_{safe_filename}") or b["pathname"] == safe_filename:
                        print(f"Deleting existing blob: {b['pathname']}")
                        vercel_blob.delete(b["url"])
            except Exception as e:
                print(f"Warning: Failed to delete existing blob: {e}")

            blob_name = f"{int(time.time())}_{safe_filename}"
            resp = vercel_blob.put(
                blob_name,
                content,
                options={"add_random_suffix": False},
            )
            
            try:
                temp_file_path.unlink()
            except Exception:
                pass
                
            return {
                "status": "completed", 
                "url": resp["url"],
                "filename": blob_name
            }
            
        else:
            with open(temp_file_path, "ab") as f:
                f.write(chunk_data)
            return {"status": "appending", "message": "Chunk appended"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chunk: {str(e)}")



@app.put("/pupload")
async def upload_file(file: UploadFile = File(...)):
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    timestamp = int(time.time())
    safe_name = Path(file.filename).name 
    blob_name = f"{timestamp}_{safe_name}"

    tmp_path = UPLOAD_DIR / blob_name

    try:
        with tmp_path.open("wb") as out_file:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                out_file.write(chunk)

        with tmp_path.open("rb") as f:
            content = f.read()

        resp = vercel_blob.put(
            blob_name,
            content,
            options={"add_random_suffix": False},
        )

        return {
            "filename": blob_name,
            "url": resp["url"],
            "status": "uploaded",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

@app.get("/download")
def download_file(filename: str):
    try:
        response = vercel_blob.list()
        blobs = response.get("blobs", [])
        
        if not blobs:
            raise HTTPException(status_code=404, detail="No blobs found")
            
        target_blob = None
        
        matches = [
            b for b in blobs 
            if b["pathname"].endswith(f"_{filename}") or b["pathname"] == filename
        ]
        
        if not matches:
             raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
             
        matches.sort(key=lambda x: x["uploadedAt"], reverse=True)
        target_blob = matches[0]
        
        url = target_blob["url"]
        blob_pathname = target_blob["pathname"]
        
        r = requests.get(url, stream=True)
        r.raise_for_status()
        
        return StreamingResponse(
            r.iter_content(chunk_size=8192),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={blob_pathname}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/latest")
def get_latest_blob():
    try:
        response = vercel_blob.list()
        blobs = response.get("blobs", [])
        
        if not blobs:
            raise HTTPException(status_code=404, detail="No blobs found")
            
        sorted_blobs = sorted(blobs, key=lambda x: x["uploadedAt"], reverse=True)
        latest_blob = sorted_blobs[0]
        
        url = latest_blob["url"]
        filename = latest_blob["pathname"]

        r = requests.get(url, stream=True)
        r.raise_for_status()
        
        return StreamingResponse(
            r.iter_content(chunk_size=8192),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)