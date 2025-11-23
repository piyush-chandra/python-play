import requests
import re
import os
import sys

BASE_URL = "http://localhost:8000"
CHUNK_SIZE = 8192  # 8KB chunks for download

def get_filename_from_cd(cd):
    """Get filename from content-disposition"""
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0].strip('"')

def download_latest():
    print("Fetching latest file...")
    
    try:
        # stream=True is key here to download in chunks
        with requests.get(f"{BASE_URL}/latest", stream=True) as r:
            r.raise_for_status()
            
            # Try to get filename from header
            cd = r.headers.get("Content-Disposition")
            filename = get_filename_from_cd(cd)
            
            if not filename:
                # Fallback if no header
                filename = f"downloaded_{int(time.time())}.bin"
                
            # Remove quotes if present
            filename = filename.strip('"')
            
            # Save to current directory
            local_path = os.path.join(os.getcwd(), f"downloaded_{filename}")
            
            print(f"Downloading to '{local_path}'...")
            
            total_size = 0
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE): 
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
                        # Print progress (overwrite line)
                        sys.stdout.write(f"\rDownloaded {total_size} bytes")
                        sys.stdout.flush()
            
            print(f"\n\nSuccess! File saved to: {local_path}")
            
    except Exception as e:
        print(f"\nError downloading file: {e}")

if __name__ == "__main__":
    download_latest()
