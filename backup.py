from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from pathlib import Path
import tempfile
import time
import vercel_blob
import httpx
from dotenv import load_dotenv
import os

load_dotenv()


token = os.getenv("BLOB_READ_WRITE_TOKEN")
print(f"Token loaded: {'Yes' if token else 'No'}")
if token:
    print(f"Token prefix: {token[:5]}...")
@app.put("/upload")
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
        blob_name = f"{timestamp}_{safe_name}"
        
        # Upload to Vercel Blob
        resp = vercel_blob.put(
            blob_name,
            content,
            options={"add_random_suffix": False},
        )
        
        return {
            "filename": blob_name,
            "url": resp["url"],
            "status": "uploaded",
            "size": len(content),
            "method": "binary-get"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


