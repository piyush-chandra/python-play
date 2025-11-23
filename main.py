from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from pathlib import Path
import tempfile
from dotenv import load_dotenv
import os
import uvicorn

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
@app.post("/test")
def test_text(request: Request):
    return request.body()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)