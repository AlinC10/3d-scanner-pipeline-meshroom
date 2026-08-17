# How it should work & Setup

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
    * Return the results (texturing 1, .stl, .glb)

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