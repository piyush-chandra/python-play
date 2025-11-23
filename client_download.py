import requests
import re
import os
import sys

BASE_URL = "http://localhost:8000"
CHUNK_SIZE = 8192  # 8KB chunks for download

def get_filename_from_cd(cd):
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0].strip('"')

def download_file(target_filename=None):
    if target_filename:
        print(f"Fetching file '{target_filename}'...")
        url = f"{BASE_URL}/download?filename={target_filename}"
    else:
        print("Fetching latest file...")
        url = f"{BASE_URL}/latest"
    
    try:
        with requests.get(url, stream=True) as r:
            if r.status_code == 404:
                print("Error: File not found.")
                return
            r.raise_for_status()
            
            cd = r.headers.get("Content-Disposition")
            filename = get_filename_from_cd(cd)
            
            if not filename:
                filename = f"downloaded_{int(time.time())}.bin"
                
            filename = filename.strip('"')
            local_path = os.path.join(os.getcwd(), f"downloaded_{filename}")
            
            print(f"Downloading to '{local_path}'...")
            
            total_size = 0
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE): 
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
                        sys.stdout.write(f"\rDownloaded {total_size} bytes")
                        sys.stdout.flush()
            
            print(f"\n\nSuccess! File saved to: {local_path}")
            
    except Exception as e:
        print(f"\nError downloading file: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        download_file(sys.argv[1])
    else:
        download_file()
