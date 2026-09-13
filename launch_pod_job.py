import os
import json
import time
import requests
from ram_heuristic import calculate_required_ram

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
GRAPHQL_URL = "https://api.runpod.io/graphql"

# Update this to your actual Docker image name on Docker Hub
IMAGE_NAME = "yourdockerhubuser/meshroom-runner:latest"

# We will determine GPU dynamically now, so remove the global GPU_TYPE_ID
# GPU_TYPE_ID = "NVIDIA GeForce RTX 5090"

def gql(query: str, variables: dict | None = None) -> dict:
    """
    Execute a GraphQL query against the RunPod API.
    
    :param query: The GraphQL query string.
    :type query: str
    :param variables: The variables for the GraphQL query.
    :type variables: dict | None
    :return: The data payload from the GraphQL response.
    :rtype: dict
    """
    if not RUNPOD_API_KEY:
        raise ValueError("RUNPOD_API_KEY is not set.")
    
    r = requests.post(
        GRAPHQL_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RUNPOD_API_KEY}",
        },
        json={"query": query, "variables": variables or {}},
        timeout=60,
    )
    r.raise_for_status()
    payload = r.json()
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]

def create_pod(env_dict: dict, gpu_type_id: str) -> str:
    """
    Create a new pod on RunPod using the specified environment and GPU.
    
    :param env_dict: The environment variables to set in the pod.
    :type env_dict: dict
    :param gpu_type_id: The ID of the GPU type to request.
    :type gpu_type_id: str
    :return: The ID of the created pod.
    :rtype: str
    """
    mutation = """
    mutation CreatePod($input: PodFindAndDeployOnDemandInput!) {
      podFindAndDeployOnDemand(input: $input) {
        id
        desiredStatus
      }
    }
    """
    env_list = [{"key": k, "value": str(v)} for k, v in env_dict.items()]

    pod_input = {
        "cloudType": "SECURE",
        "gpuCount": 1,
        "gpuTypeId": gpu_type_id,
        "name": f"meshroom-dynamic-job",
        "imageName": IMAGE_NAME,
        # Give enough disk space to extract the 22.5 GB Meshroom + cache + output
        "containerDiskInGb": 60, 
        "volumeInGb": 0,         
        "env": env_list,
        "ports": "",
        "dockerArgs": "",
    }

    data = gql(mutation, {"input": pod_input})
    return data["podFindAndDeployOnDemand"]["id"]

def get_pod_status(pod_id: str) -> dict:
    """
    Retrieve the status of a specific pod.
    
    :param pod_id: The ID of the pod to check.
    :type pod_id: str
    :return: The pod status data.
    :rtype: dict
    """
    query = """
    query GetPod($podId: String!) {
      pod(input: {podId: $podId}) {
        id
        desiredStatus
        runtime {
          uptimeInSeconds
        }
      }
    }
    """
    data = gql(query, {"podId": pod_id})
    return data["pod"]

def stop_pod(pod_id: str) -> str:
    """
    Stop a running pod on RunPod.
    :param pod_id: The ID of the pod to stop.
    :type pod_id: str
    :return: The desired status of the pod after stopping.
    :rtype: str
    """
    mutation = """
    mutation StopPod($podId: String!) {
      podStop(input: {podId: $podId}) {
        id
        desiredStatus
      }
    }
    """
    data = gql(mutation, {"podId": pod_id})
    return data["podStop"]["desiredStatus"]

def launch_job(job: dict):
    """
    Launch a processing job on a dynamically provisioned pod based on RAM requirements.
    
    :param job: The job configuration and details.
    :type job: dict
    :return: True if the job completed successfully.
    :rtype: bool
    """
    photo_count = job.get("photo_count", 50)
    resolution_mp = job.get("resolution_mp", 12.0)
    mode = job.get("mode", "single")
    two_sides = (mode == "two-sides")
    
    # Calculate required RAM
    ram_min_gb = calculate_required_ram(
        num_images=photo_count,
        resolution_mp=resolution_mp,
        depthmap_downscale=2,
        max_input_points=10000000,
        two_sides_mode=two_sides
    )
    print(f"Calculated required RAM: {ram_min_gb} GB for {photo_count} photos ({mode} mode)")

    # Define GPU fallback strategy based on required RAM and Secure Cloud availability
    if ram_min_gb > 64:
        # High RAM needs:
        # 1. Try 5090 (sometimes it has 94GB)
        # 2. Try L40 (Ada Lovelace, very fast, huge 250GB RAM at $0.82/hr)
        # 3. Try RTX 6000 Ada Generation (Ada Lovelace, very fast)
        # 4. Try RTX 3090 (Ampere, slower but very cheap at $0.50/hr and often has 125GB RAM)
        # 5. Fallback to RTX A6000 (Ampere, similar speed to 3090)
        gpu_fallback_list = [
            "NVIDIA GeForce RTX 5090",
            "NVIDIA L40",
            "NVIDIA RTX 6000 Ada Generation",
            "NVIDIA GeForce RTX 3090",
            "NVIDIA RTX A6000"
        ]
        complementary_gpus_list = [
            "NVIDIA GeForce RTX 4090",
            "NVIDIA A40"                  
                                   ]
    else:
        # Low/Medium RAM needs: Stick to fast/cheap consumer GPUs.
        gpu_fallback_list = [
            "NVIDIA GeForce RTX 5090",
            "NVIDIA GeForce RTX 4090",
            "NVIDIA GeForce RTX 3090",
            "NVIDIA A40"
        ]
        complementary_gpus_list = [
            "NVIDIA L40",
            "NVIDIA RTX 6000 Ada Generation",
            "NVIDIA RTX A6000"
        ]

    # Prepare environment variables for the pod
    env = {
        "JOB_JSON": json.dumps(job),
        "RAM_MIN_GB": str(ram_min_gb),
    }
    
    # Forward Cloudflare R2 secrets or Fallback URLs if they exist locally
    for key in ["R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "MESHROOM_FALLBACK_URL"]:
        if os.getenv(key):
            env[key] = os.getenv(key)

    # Loop continuously until we successfully run a pod
    attempt = 1
    while True:
        for target_gpu in gpu_fallback_list:
            print(f"\n--- Attempt {attempt} (Targeting: {target_gpu}) ---")
            attempt += 1
            
            try:
                pod_id = create_pod(env, target_gpu)
                print(f"Created pod: {pod_id}")
            except Exception as e:
                print(f"Failed to create pod for {target_gpu}: {e}")
                print("Trying next GPU in fallback list...")
                
                if attempt / len(gpu_fallback_list) == 4 and attempt % len(gpu_fallback_list) == 0:
                    gpu_fallback_list.extend(complementary_gpus_list)
                
                time.sleep(2)
                continue

            print("Waiting for pod to start and complete...")
            uptime = 0
            while True:
                time.sleep(15)
                pod_data = get_pod_status(pod_id)
                status = pod_data["desiredStatus"]
                
                runtime = pod_data.get("runtime")
                if runtime:
                    uptime = runtime.get("uptimeInSeconds", 0)
                    
                print(f"Pod status: {status} (Uptime: {uptime}s)")

                if status in ("EXITED", "TERMINATED"):
                    print("Pod has exited.")
                    break

            print(f"Stopping/cleaning up pod {pod_id}...")
            stop_pod(pod_id)
            
            # If the pod exited in under 120 seconds, we assume it failed the RAM check.
            if uptime > 120:
                print("Pod ran for a significant amount of time. Assuming job success!")
                return True
            else:
                print("Pod exited very quickly. RAM check likely failed on this host. Retrying...")
                time.sleep(10) # Cooldown before trying a new pod
                
        print("\n[!] Cycled through the entire GPU list without success.")
        print("Waiting 60 seconds before restarting the cycle to avoid spamming the API...")
        time.sleep(60)

if __name__ == "__main__":
    test_job = {
        "job_id": "job-12345",
        "photo_count": 80,
        "mode": "single"
    }
    launch_job(test_job)

