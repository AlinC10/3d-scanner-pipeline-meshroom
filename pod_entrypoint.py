import os
import sys
import json
import tarfile
import urllib.request
import shutil
from main import run_pipeline

MESHROOM_URL = "https://zenodo.org/records/16887472/files/Meshroom-2025.1.0-Linux.tar.gz"
# Provide a fallback URL here (e.g., your R2 bucket or a free HuggingFace Dataset link)
MESHROOM_FALLBACK_URL = os.getenv("MESHROOM_FALLBACK_URL", "") 
DOWNLOAD_PATH = "/workspace/Meshroom.tar.gz"
EXTRACT_PATH = "/workspace"
MESHROOM_DIR = os.path.join(EXTRACT_PATH, "Meshroom-2025.1.0")
MESHROOM_EXE = os.path.join(MESHROOM_DIR, "meshroom_batch")

def mem_total_gb() -> int:
    """
    Get the total system memory in gigabytes.
    :return: The total memory in GB.
    :rtype: int
    """
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return int(kb / 1024 / 1024)
    except Exception as e:
        print(f"Could not read /proc/meminfo: {e}")
    return 0

def download_and_extract_meshroom():
    """
    Download and extract the Meshroom package.
    :return: None
    :rtype: None
    """
    if os.path.exists(MESHROOM_EXE):
        print(f"[boot] Meshroom already exists at {MESHROOM_EXE}, skipping download.")
        return

    print(f"[boot] Downloading Meshroom from {MESHROOM_URL} ...")
    os.makedirs(EXTRACT_PATH, exist_ok=True)
    
    try:
        urllib.request.urlretrieve(MESHROOM_URL, DOWNLOAD_PATH)
    except Exception as e:
        print(f"[boot] WARNING: Failed to download from primary URL: {e}")
        if MESHROOM_FALLBACK_URL:
            print(f"[boot] Attempting to download from fallback URL: {MESHROOM_FALLBACK_URL}")
            urllib.request.urlretrieve(MESHROOM_FALLBACK_URL, DOWNLOAD_PATH)
        else:
            print("[boot] CRITICAL: No fallback URL provided and primary failed.")
            sys.exit(1)
    print("[boot] Download complete. Extracting...")
    
    with tarfile.open(DOWNLOAD_PATH, "r:gz") as tar:
        tar.extractall(path=EXTRACT_PATH)
    
    print("[boot] Extraction complete.")
    
    print("[boot] Cleaning up unused UI components to save space...")
    ui_components = ["Meshroom", "qtPlugins"]
    for comp in ui_components:
        comp_path = os.path.join(MESHROOM_DIR, comp)
        if os.path.exists(comp_path):
            if os.path.isdir(comp_path):
                shutil.rmtree(comp_path)
            else:
                os.remove(comp_path)
    
    if os.path.exists(DOWNLOAD_PATH):
        os.remove(DOWNLOAD_PATH)
    
    print("[boot] Meshroom ready.")

if __name__ == "__main__":
    job_json_str = os.getenv("JOB_JSON", '{"input": {"mode": "single"}}')
    job = json.loads(job_json_str)

    ram_min_gb = int(float(os.getenv("RAM_MIN_GB", "32")))
    local_sim = os.getenv("LOCAL_SIMULATION", "0") == "1"

    total_gb = mem_total_gb()
    print(f"[boot] System RAM total: {total_gb} GB, required >= {ram_min_gb} GB")

    if total_gb > 0 and total_gb < ram_min_gb:
        print(f"[boot] ERROR: Insufficient RAM. Expected at least {ram_min_gb} GB.")
        sys.exit(42)

    if not local_sim:
        os.environ["MESHROOM_EXE"] = MESHROOM_EXE
        download_and_extract_meshroom()
    else:
        print("[boot] LOCAL_SIMULATION=1. Skipping Meshroom download.")
        # When simulating locally, use the mounted path
        os.environ["MESHROOM_EXE"] = "/runpod-volume/Meshroom-2025.1.0/meshroom_batch"

    print("[boot] Starting pipeline...")
    try:
        run_pipeline(job)
        print("[boot] Pipeline completed successfully!")
    except Exception as e:
        print(f"[boot] Pipeline failed: {e}")
        sys.exit(1)

    print("[boot] Done, exiting cleanly.")

