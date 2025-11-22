from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from pathlib import Path
import tempfile
import time
import vercel_blob
import httpx

app = FastAPI()

# Directory for short-lived temp files (auto-deleted after upload)
UPLOAD_DIR = Path(tempfile.gettempdir()) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 1024 * 1024  # 1 MB


@app.get("/")
def read_root():
    return {"message": "FastAPI file streamer is up"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Uploads file from client → temp disk → Vercel Blob.
    Temp file is deleted after upload.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Use timestamp for ordering and uniqueness
    timestamp = int(time.time())
    safe_name = Path(file.filename).name  # remove any path components
    blob_name = f"{timestamp}_{safe_name}"

    tmp_path = UPLOAD_DIR / blob_name

    try:
        # 1) Save incoming upload to a temp file in chunks
        with tmp_path.open("wb") as out_file:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                out_file.write(chunk)

        # 2) Read from temp file and upload to Vercel Blob
        # NOTE: vercel_blob.put currently expects bytes, so we read the file fully here.
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
        # 3) Clean up local temp file
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                # best effort cleanup; don't crash if delete fails
                pass


@app.get("/latest")
def get_latest_file():
    """
    Returns an HTTP redirect to the latest .zip file in Vercel Blob.
    Client downloads directly from Blob.
    """
    try:
        blobs = vercel_blob.list()
        zip_blobs = [b for b in blobs.get("blobs", []) if b["pathname"].endswith(".zip")]

        if not zip_blobs:
            raise HTTPException(status_code=404, detail="No .zip files uploaded")

        latest_blob = max(zip_blobs, key=lambda x: x["uploadedAt"])
        return RedirectResponse(url=latest_blob["url"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve latest file: {str(e)}")


@app.get("/latest/stream")
async def stream_latest_file():
    """
    Streams the latest .zip file from Vercel Blob through this server
    (hides Blob URL, allows you to add auth, etc.).
    """
    try:
        blobs = vercel_blob.list()
        zip_blobs = [b for b in blobs.get("blobs", []) if b["pathname"].endswith(".zip")]

        if not zip_blobs:
            raise HTTPException(status_code=404, detail="No .zip files uploaded")

        latest_blob = max(zip_blobs, key=lambda x: x["uploadedAt"])
        blob_url = latest_blob["url"]
        filename = latest_blob["pathname"]

        async def iter_blob():
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", blob_url, timeout=None) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.aiter_bytes():
                        yield chunk

        return StreamingResponse(
            iter_blob(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stream latest file: {str(e)}")


@app.post("/stream")
async def stream_file(file: UploadFile = File(...)):
    """
    Simple echo-stream endpoint: streams the uploaded file back to the caller.
    Useful for testing streaming behavior.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    return StreamingResponse(
        file.file,
        media_type=file.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file.filename}"'},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
