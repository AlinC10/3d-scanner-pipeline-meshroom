## 1. File & Metadata Processing (Pre-Meshroom)
*   [x] **EXIF Modification (Python Script):** Write a Python script to modify the `Camera Model` metadata field (e.g., from "IMX477" to "IMX477_Cam2") exclusively for Camera 2's photos. This forces Meshroom to calculate distinct lens profiles for the slight focus differences.
*   [x] **File name synchronization:** Ensure that photos taken at the exact same moment (same turntable angle) have identical names for both cameras (e.g., both should be named `0001.jpg`).
*   [x] **Rig folder structure setup:** Arrange the images into the required folder hierarchy to "lock" the 30° angle between the cameras. Documentation: [Multi-Camera Rig Meshroom](https://meshroom-manual.readthedocs.io/en/latest/faq/multi-camera-rig/multi-camera-rig.html)
    *   Parent folder `rig/`
    *   Sub-folder `rig/0/` -> contains Camera 1 images
    *   Sub-folder `rig/1/` -> contains Camera 2 images (with the modified metadata)
    *   **Implementation:** Pass `{"input": {"mode": "rig"}}` in the RunPod job payload to activate. Default is `"single"` (flat `input_images/` folder). For local simulation use `send_rig_images()` from `simulation.py`.

## 2. Meshroom Pipeline Update (v2025.1)
*   [ ] **New project setup & template selection:** Create a new project by choosing between two dynamic pipeline options depending on your scanning needs:

    * **Basic 360° Scan (template_turntable.mg):** Use this single-pass template for a standard 360° rotation on the platan without flipping the object. It utilizes built-in AI background removal and processes much faster.
    * **Full 360° Scan (template_two_sides.mg):** Use this dual-pass template if the user chooses to flip the object at the end to capture the base. This pipeline takes double the time as it processes two separate sets of images and merges them using SfMMerge.
*   [ ] **Folder Structure for Two Sides:** For the second pipeline (template_two_sides.mg), set up two distinct parent directories (rig1/ and rig2/), each containing the required synchronized subfolders (e.g., rig1/0/, rig1/1/ for the first position and rig2/0/, rig2/1/ for the flipped position).
*   [x] **Migrate final nodes:** Copy your custom final nodes (Meshing, Filtering, Texturing - the branches for the 2 objects) from the old *Default Photogrammetry* project.
*   [x] **Convert to .stl and .3mf for 3D Printing**
*   [ ] **Connect to the new pipeline:** Paste the copied nodes into the new Turntable project. Delete the default final nodes from the new template that you do not need, and reconnect your custom ones to the main flow (usually to *StructureFromMotion* or *DepthMap*). Import the `rig/` folder to begin processing




## How it should work & Setup

* Buy a Network Volume from Runpod which will hold Meshroom. For Meshroom installation:
    * Rent a GPU Pod
    * Mount the Network Volume to the GPU Pod
    * Install Meshroom on the Network Volume
    * Close GPU Pod

*  Workflow:
    * Rent a GPU for Serverless Endpoint
    * Run a local Python Script that will call the serverless endpoint and wait for the result.
    * Upload the Docker Image
    * Mount the Network Volume to the GPU Serverless Endpoint
    * Run the Pipeline (Download Images from Cloudflare R2 -> Run Meshroom -> Upload to Cloudflare R2 -> Retrieve Result to Raspberry Pi)
    * Return the results (texturing 1, texturing 2, .stl, .glb, .3mf)

* Docker Image:
    * FROM nvidia/cuda:13.3.1-runtime-ubuntu24.04
    * apt-get update && apt-get -y upgrade
    * install Python (3.12)
    * copy main.py, images.py, requirements.txt, template.mg (handler.py) to the Docker image
    * install dependencies (pip install -r requirements.txt)
    * install NVIDIA Cuda Drivers
    * run Pipeline Python


## How local file should look
* Submit the Job: Raspberry PI sends the request to the endpoint. RunPod immediately responds with a job_id and a status of IN_QUEUE, and the initial connection closes.

* Poll for Status: Raspberry PI runs a script that periodically asks the /status/{job_id} endpoint, "Are you done yet?".

* Receive the Link: Once the photogrammetry finishes, the /status check returns a status of COMPLETED. The response payload will contain the download_link that your RunPod server generated.

* Auto-Download: Raspberry PI takes that link, downloads the .zip file, and saves it directly to your hard drive. (Note: Async job results are retained by RunPod for 30 minutes after completion).

```python
import requests
import time
import os

# Your RunPod Details
ENDPOINT_ID = "YOUR_ENDPOINT_ID"
API_KEY = "YOUR_RUNPOD_API_KEY"
BASE_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def run_photogrammetry_automation():
    print("1. Submitting job to RunPod...")
    
    # 1. Send the Async request
    response = requests.post(
        f"{BASE_URL}/run",
        headers=HEADERS,
        json={"input": {"image_folder": "YOUR_INPUT_DATA"}} 
    )
    
    job_id = response.json()["id"]
    print(f"Job submitted successfully! Job ID: {job_id}")
    
    # 2. Poll the Status API
    print("2. Waiting for Meshroom to finish processing...")
    status_url = f"{BASE_URL}/status/{job_id}"
    
    while True:
        status_response = requests.get(status_url, headers=HEADERS).json()
        status = status_response["status"]
        
        if status == "COMPLETED":
            # The job finished! Extract the download link we made earlier
            print("\nProcessing Complete!")
            download_url = status_response["output"]["download_link"]
            break
            
        elif status in ["FAILED", "CANCELLED", "TIMED_OUT"]:
            print(f"\nJob failed with status: {status}")
            return
            
        else:
            # Status is IN_QUEUE or IN_PROGRESS. Wait 15 seconds and check again.
            print(f"Status: {status}... checking again in 15 seconds.")
            time.sleep(15)

    # 3. Automatically Download the File
    print(f"3. Downloading 3D model from: {download_url}")
    save_path = os.path.join(os.getcwd(), f"{job_id}_model.zip")
    
    download_response = requests.get(download_url, stream=True)
    with open(save_path, 'wb') as file:
        for chunk in download_response.iter_content(chunk_size=8192):
            file.write(chunk)
            
    print(f"Success! Your 3D model is saved at: {save_path}")

if __name__ == "__main__":
    run_photogrammetry_automation()
```
