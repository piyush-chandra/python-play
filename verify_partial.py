import requests
import base64
import time

BASE_URL = "http://localhost:8000"

def test_single_chunk_upload():
    print("Testing Single Chunk Upload...")
    filename = "small_test.txt"
    content = b"This is a small file less than 100KB."
    data_b64 = base64.b64encode(content).decode('utf-8')
    
    payload = {
        "data": data_b64,
        "chunkNumber": 1,
        "totalChunks": 1,
        "fileName": filename,
        "isStarted": True,
        "isCompleted": True
    }
    
    try:
        r = requests.post(f"{BASE_URL}/test1", json=payload)
        print(f"Response: {r.status_code} - {r.json()}")
        assert r.status_code == 200
        json_resp = r.json()
        assert json_resp.get("status") == "completed"
        assert json_resp.get("url") is not None
        print("Single chunk upload SUCCESS")
        return json_resp.get("url")
    except Exception as e:
        print(f"Single chunk upload FAILED: {e}")
        raise

def test_partial_download():
    print("\nTesting Partial Download...")
    # Wait a bit for consistency
    time.sleep(2)
    
    try:
        r = requests.get(f"{BASE_URL}/latest/partial")
        print(f"Response: {r.status_code}")
        assert r.status_code in [200, 206]
        
        content = r.content
        print(f"Content Length: {len(content)}")
        print(f"Content Preview: {content[:50]}")
        
        assert len(content) <= 8192
        assert b"This is a small file" in content
        print("Partial download SUCCESS")
        
    except Exception as e:
        print(f"Partial download FAILED: {e}")
        raise

if __name__ == "__main__":
    try:
        test_single_chunk_upload()
        test_partial_download()
        print("\nALL TESTS PASSED")
    except Exception as e:
        print(f"\nTESTS FAILED")
        exit(1)
