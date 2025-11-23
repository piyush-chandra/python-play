# import requests
# import time

# BASE_URL = "http://localhost:8000"

# def test_chunked_upload():
#     print("Testing Chunked Upload...")
    
#     # 1. Start
#     payload_start = {
#         "text": "Part 1: Start of the file.\n",
#         "isStarted": True,
#         "isCompleted": False
#     }
#     r = requests.post(f"{BASE_URL}/test", json=payload_start)
#     print(f"Start: {r.status_code} - {r.json()}")
#     assert r.status_code == 200

#     # 2. Append
#     payload_mid = {
#         "text": "Part 2: Middle of the file.\n",
#         "isStarted": False,
#         "isCompleted": False
#     }
#     r = requests.post(f"{BASE_URL}/test", json=payload_mid)
#     print(f"Append: {r.status_code} - {r.json()}")
#     assert r.status_code == 200

#     # 3. Complete
#     payload_end = {
#         "text": "Part 3: End of the file.",
#         "isStarted": False,
#         "isCompleted": True
#     }
#     r = requests.post(f"{BASE_URL}/test", json=payload_end)
#     print(f"Complete: {r.status_code} - {r.json()}")
#     assert r.status_code == 200
    
#     blob_url = r.json().get("url")
#     print(f"Blob URL: {blob_url}")
#     return blob_url

# def test_latest_download(expected_url):
#     print("\nTesting Latest Download...")
#     # Allow some time for eventual consistency if needed, though usually fast
#     time.sleep(2) 
    
#     r = requests.get(f"{BASE_URL}/latest", allow_redirects=False)
#     print(f"Latest Redirect Status: {r.status_code}")
    
#     if r.status_code == 307:
#         location = r.headers['Location']
#         print(f"Redirect Location: {location}")
#         # Note: The URL might be slightly different (e.g. query params) but base should match
#         # or we can just fetch the content and verify it matches
        
#         content_r = requests.get(location)
#         print(f"Content: {content_r.text}")
#         assert "Part 1" in content_r.text
#         assert "Part 3" in content_r.text
#     else:
#         print("Did not redirect as expected (307).")
#         # If it followed redirect automatically (if allow_redirects=True default)
#         # requests.get follows by default, but I set False above.
#         pass

# if __name__ == "__main__":
#     try:
#         url = test_chunked_upload()
#         test_latest_download(url)
#         print("\nSUCCESS: All tests passed!")
#     except Exception as e:
#         print(f"\nFAILURE: {e}")
