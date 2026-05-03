from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from pathlib import Path
import tempfile
import time
import httpx
from dotenv import load_dotenv
import os
import r2_storage

load_dotenv()


r2_bucket = os.getenv("R2_BUCKET_NAME")
print(f"R2 bucket configured: {'Yes' if r2_bucket else 'No'}")
@app.put("/upload")
async def upload_file(file: UploadFile = File(...)):
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    timestamp = int(time.time())
    safe_name = Path(file.filename).name 
    object_name = f"{timestamp}_{safe_name}"

    tmp_path = UPLOAD_DIR / object_name

    try:
        with tmp_path.open("wb") as out_file:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                out_file.write(chunk)

        with tmp_path.open("rb") as f:
            content = f.read()

        resp = r2_storage.put_object(object_name, content, file.content_type)

        return {
            "filename": object_name,
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


@app.get("/helloworld")
async def upload_binary(request: Request):
    try:
        filename = request.headers.get("X-Filename") or request.headers.get("x-filename")
        
        if not filename:
            raise HTTPException(status_code=400, detail="Missing X-Filename header")
        
        # Read raw binary body
        content = await request.body()
        
        if not content:
            raise HTTPException(status_code=400, detail="Empty request body")
        
        # Use timestamp for ordering
        timestamp = int(time.time())
        safe_name = Path(filename).name
        object_name = f"{timestamp}_{safe_name}"
        
        resp = r2_storage.put_object(object_name, content)
        
        return {
            "filename": object_name,
            "url": resp["url"],
            "status": "uploaded",
            "size": len(content),
            "method": "binary-get"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

