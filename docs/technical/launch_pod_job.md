# `launch_pod_job.py`

## API Reference

- **`RUNPOD_API_KEY`** = `os.environ.get('RUNPOD_API_KEY')`
- **`GRAPHQL_URL`** = `'https://api.runpod.io/graphql'`
- **`IMAGE_NAME`** = `'yourdockerhubuser/meshroom-runner:latest'`
### `def gql(query, variables=None)`
> Execute a GraphQL query against the RunPod API.
> 
> :param query: The GraphQL query string.
> :type query: str
> :param variables: The variables for the GraphQL query.
> :type variables: dict | None
> :return: The data payload from the GraphQL response.
> :rtype: dict

### `def create_pod(env_dict, gpu_type_id)`
> Create a new pod on RunPod using the specified environment and GPU.
> 
> :param env_dict: The environment variables to set in the pod.
> :type env_dict: dict
> :param gpu_type_id: The ID of the GPU type to request.
> :type gpu_type_id: str
> :return: The ID of the created pod.
> :rtype: str

### `def get_pod_status(pod_id)`
> Retrieve the status of a specific pod.
> 
> :param pod_id: The ID of the pod to check.
> :type pod_id: str
> :return: The pod status data.
> :rtype: dict

### `def stop_pod(pod_id)`
> Stop a running pod on RunPod.
> :param pod_id: The ID of the pod to stop.
> :type pod_id: str
> :return: The desired status of the pod after stopping.
> :rtype: str

### `def launch_job(job)`
> Launch a processing job on a dynamically provisioned pod based on RAM requirements.
> 
> :param job: The job configuration and details.
> :type job: dict
> :return: True if the job completed successfully.
> :rtype: bool
