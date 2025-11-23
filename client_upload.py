import requests
import base64
import os
import math
import sys
import time

BASE_URL = "http://localhost:8000"
CHUNK_SIZE = 100 * 1024  # 100KB

def upload_file(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    file_size = os.path.getsize(file_path)
    total_chunks = math.ceil(file_size / CHUNK_SIZE)
    filename = os.path.basename(file_path)

    print(f"Uploading '{filename}' ({file_size} bytes) in {total_chunks} chunks...")

    with open(file_path, "rb") as f:
        chunk_number = 1
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break

            is_started = (chunk_number == 1)
            is_completed = (chunk_number == total_chunks)
            
            # Base64 encode
            data_b64 = base64.b64encode(chunk).decode('utf-8')

            payload = {
                "data": data_b64,
                "chunkNumber": chunk_number,
                "totalChunks": total_chunks,
                "fileName": filename,
                "isStarted": is_started,
                "isCompleted": is_completed
            }

            try:
                response = requests.post(f"{BASE_URL}/test1", json=payload)
                response.raise_for_status()
                result = response.json()
                
                print(f"Chunk {chunk_number}/{total_chunks}: {result.get('status')} - {result.get('message', '')}")
                
                if is_completed:
                    print("\nUpload Complete!")
                    print(f"Blob URL: {result.get('url')}")
                    
            except requests.exceptions.RequestException as e:
                print(f"\nError uploading chunk {chunk_number}: {e}")
                return

            chunk_number += 1
            # Optional: small delay to not overwhelm if needed, but local is fine
            # time.sleep(0.01) 

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client_upload.py <file_path>")
    else:
        upload_file(sys.argv[1])
