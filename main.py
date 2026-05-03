from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import tempfile
from dotenv import load_dotenv
import time
import os
import uvicorn
import base64
import r2_storage

load_dotenv()

r2_bucket = os.getenv("R2_BUCKET_NAME")
print(f"R2 bucket configured: {'Yes' if r2_bucket else 'No'}")

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
        elif chunk_data:
            with open(temp_file_path, "ab") as f:
                f.write(chunk_data)
        
        if payload.isCompleted:
            if not temp_file_path.exists():
                 raise HTTPException(status_code=400, detail="Upload session not found (file missing)")
                 
            with open(temp_file_path, "rb") as f:
                content = f.read()
            
            # Overwrite Logic: Delete existing R2 objects with same suffix
            try:
                r2_storage.delete_matching_filename(safe_filename)
            except Exception as e:
                print(f"Warning: Failed to delete existing R2 object: {e}")

            object_name = f"{int(time.time())}_{safe_filename}"
            resp = r2_storage.put_object(object_name, content)
            
            # Cleanup
            try:
                temp_file_path.unlink()
            except Exception:
                pass
                
            return {
                "status": "completed", 
                "url": resp["url"],
                "filename": object_name
            }
            
        if payload.isStarted:
             return {"status": "started", "message": "File initialized"}
        else:
             return {"status": "appending", "message": "Chunk appended"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chunk: {str(e)}")



@app.put("/pupload")
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

@app.get("/download")
def download_file(filename: str):
    try:
        target_object = r2_storage.find_latest_by_filename(filename)

        if not target_object:
             raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        object_key = target_object["key"]
        r2_response = r2_storage.get_object_stream(object_key)
        
        return StreamingResponse(
            r2_storage.iter_body(r2_response["Body"], chunk_size=8192),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={object_key}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/latest")
def get_latest_object():
    try:
        latest_object = r2_storage.latest_object()

        if not latest_object:
            raise HTTPException(status_code=404, detail="No R2 objects found")

        filename = latest_object["key"]
        r2_response = r2_storage.get_object_stream(filename)
        
        return StreamingResponse(
            r2_storage.iter_body(r2_response["Body"], chunk_size=8192),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/latest/partial")
def get_latest_partial():
    try:
        latest_object = r2_storage.latest_object()

        if not latest_object:
            raise HTTPException(status_code=404, detail="No R2 objects found")

        filename = latest_object["key"]
        r2_response = r2_storage.get_object_stream(filename, byte_range="bytes=0-8191")
        content = r2_response["Body"].read()
        r2_response["Body"].close()
            
        return StreamingResponse(
            iter([content]),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=partial_{filename}",
                "Content-Length": str(len(content))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
