# Meshroom Photogrammetry Pipeline

Automated 3D model generation from photographs using [AliceVision/Meshroom](https://alicevision.org/), producing three distinct output variants simultaneously. The pipeline is containerized using Docker and is designed for deployment as a serverless API on the **RunPod** platform.

| Output | Format | Purpose |
|---|---|---|
| **High-poly models** | `.obj` + `.png`, `.glb`, `.stl`, `.3mf` | High fidelity assets for VFX, gaming, detailed visualization, and high-res printing. |
| **Low-poly models** | `.obj` + `.jpg`, `.glb`, `.stl`, `.3mf` | Optimized assets for web/mobile applications, fast loading, and quick prototyping. |

## How It Works

```text
Input Images (Downloaded from Cloudflare R2)
        │
        ▼
┌───────────────────┐
│  Meshroom Engine   │  (AliceVision - photogrammetry)
│                   │
│  CameraInit ──► FeatureExtraction ──► ... ──► Meshing ──► MeshFiltering
│                                                               │
│                                          ┌────────────────────┼────────────────────┐
│                                          │                    │                    │
│                                    Texturing_1          MeshDecimate         (fork)
│                                    (High: 4096px PNG)        │
│                                          │             MeshFiltering_2
│                                          │                    │
│                                          │             Texturing_2
│                                          │             (Low: 2048px JPG)
└──────────────────────────────────────────┼────────────────────┘
                                           │                    │
                                           ▼                    ▼
                                 ┌───────────────────┐  ┌───────────────────┐
                                 │    High Branch    │  │    Low Branch     │
                                 │   Post-Processing │  │   Post-Processing │
                                 │      (trimesh)    │  │      (trimesh)    │
                                 └─────────┬─────────┘  └─────────┬─────────┘
                                           │                      │
                                           ▼                      ▼
                            - Texturing_1/ (OBJ+PNG)     - Texturing_2/ (OBJ+JPG)
                            - high_model.stl             - low_model.stl
                            - high_model.3mf             - low_model.3mf
                            - high_model.glb (Draco)     - low_model.glb (Draco)
```

The core orchestration is handled by Python (`main.py`):
1. **Pre-processing**: Downloads input photographs from a Cloudflare R2 bucket.
2. **Photogrammetry**: Runs `meshroom_batch` headless (no GUI) to process the images and generate the base geometry.
3. **Branching**:
   - The **High Branch** generates a detailed `.obj` with 4096px `.png` textures.
   - The **Low Branch** decimates the mesh and generates a lightweight `.obj` with 2048px `.jpg` textures.
4. **Post-processing (Both Branches)**:
   - The raw `.obj` + texture maps (PNG/JPG) are preserved for traditional 3D workflows.
   - Both models are loaded via `trimesh`, holes are filled to make them watertight, and they are exported as **`.stl`** and **`.3mf`** formats for 3D printing.
   - Both models are packed with their materials and textures into binary **`.glb`** files for web deployment. The `.glb` files undergo **Draco Compression**, stripping raw floating-point geometry and replacing it with an arithmetic-compressed Draco blob to drastically reduce file size.
5. **Delivery**: Zips all the generated assets and uploads them back to Cloudflare R2.

## Architecture & Serverless Deployment

This project is built to run on **RunPod** as a Serverless API endpoint. Key files for the serverless setup include:

- `Dockerfile`: Packages the Python environment, dependencies, and scripts into a container.
- `requirements.txt`: Python dependencies (`trimesh`, `boto3`, `python-dotenv`).
- `config.py`: Environment configurations and paths (e.g., R2 buckets, Meshroom executable path).
- `main.py`: Core pipeline orchestration.
- `upload_files.py` / `download_files.py`: Handlers for interacting with Cloudflare R2 storage.

### RunPod Workflow
1. A client (e.g., Raspberry Pi) submits a job to the RunPod endpoint.
2. The serverless GPU worker spins up, downloads images from Cloudflare R2, and processes them using Meshroom.
3. Once completed, the outputs are zipped and uploaded back to Cloudflare R2.
4. The client polls for the job status and downloads the `.zip` containing the 3D models when ready.

## Dataset

This pipeline has been tested using the [dataset_monstree](https://github.com/alicevision/dataset_monstree) repository provided by AliceVision.

## Prerequisites

- **Meshroom 2025.1.0** — [Download](https://alicevision.org/#meshroom) (for local testing/development)
- **Python 3.10+** with a virtual environment
- **CUDA-capable GPU** (required by AliceVision for depth map computation)
- **Docker** (for building the serverless image)
- **Cloudflare R2** account and credentials

## Setup

```bash
# Clone the repository
git clone <repo-url>
cd meshroom_test

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / Docker
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration (.env)

Create a `.env` file in the project root directory and set your R2 credentials and Meshroom path:

```env
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
```

## Operating Modes

The serverless pipeline supports three different operational modes depending on how you captured your images. You specify the mode via the RunPod job payload: `{"input": {"mode": "<mode-name>"}}`.

### 1. `single` Mode (Default)
Use this for standard captures (e.g. drone mapping, handheld free-scanning).
- **Template**: `template.mg`
- **Payload**: `{"input": {"mode": "single"}}`
- **R2 Bucket Setup**: Upload images directly to the root of the bucket.
  - `IMG_0001.jpg`
  - `IMG_0002.jpg`

### 2. `rig` Mode
Use this for multi-camera captures (e.g., a turntable with 2 cameras separated by an angle).
- **Template**: `template.mg`
- **Payload**: `{"input": {"mode": "rig"}}`
- **R2 Bucket Setup**: Group images into folders named `rig/0/`, `rig/1/`, etc. (representing Camera 1 and Camera 2).
  - `rig/0/0001.jpg`
  - `rig/1/0001.jpg`

### 3. `two-sides` Mode
Use this for full 360° object scanning where you scan the object upright, flip it over, and scan the bottom. The pipeline processes both positions and merges them using `SfMMerge`.
- **Template**: `template_two_sides.mg` (Uses two `CameraInit` nodes).
- **Payload**: `{"input": {"mode": "two-sides"}}`
- **R2 Bucket Setup**: Group images into `rig1/` (upright) and `rig2/` (flipped), maintaining camera subfolders.
  - `rig1/0/0001.jpg`
  - `rig1/1/0001.jpg`
  - `rig2/0/0001.jpg`
  - `rig2/1/0001.jpg`
- **Note**: Because the Meshroom CLI does not support feeding multiple `CameraInit` nodes simultaneously via the `--input` flag, the Python orchestrator uses `aliceVision_cameraInit` to dynamically generate `.sfm` files for each rig and injects them directly into the `.mg` JSON at runtime.

## Usage

### 1. Local Simulation

You can simulate the entire flow locally using `simulation.py`:

```bash
python simulation.py
```
This script will:
- Upload images from local `input_images/` to R2 (can simulate single, rig, or two-sides uploading).
- Run the Docker container to process them.
- Download the generated `output.zip` from R2.
- Clean up the R2 bucket.

### 2. Manual Pipeline Execution

To run the pipeline directly without the simulation wrapper:

```bash
python main.py
```

### 3. Build Docker Image

```bash
docker build -t meshroom_pipeline .
```

## Pipeline Settings

### High Branch (Texturing_1)
| Setting | Value |
|---|---|
| Texture Side | 4096 |
| Downscale | 1 |
| Color Format | PNG (lossless) |
| Unwrap Method | Basic |

### Low Branch (Texturing_2)
| Setting | Value |
|---|---|
| Max Vertices (MeshDecimate) | 50,000 |
| Simplification Factor (MeshDecimate) | 0.05 |
| Keep Largest Mesh Only | true |
| Smoothing Iterations | 2 |
| Texture Side | 2048 |
| Downscale | 2 |
| Color Format | JPG (compressed) |
| Unwrap Method | Basic |

## Web Optimization (Draco Compression)

The pipeline integrates **Draco Geometry Compression** (`KHR_draco_mesh_compression`) via Python (`DracoPy` and `pygltflib`) during the `.glb` export stage.

### Why is it used?
Raw 3D geometry (floats for X,Y,Z positions and UV maps) is bulky. Even a low-poly 30k vertex model can take up several megabytes of raw geometry. Draco is an arithmetic coding algorithm that shrinks this 3D data by **80-90%**.
- **Before Draco:** ~35 MB `.glb`
- **After Draco:** ~4.7 MB `.glb`

### The Speed Tradeoff
Draco introduces an intentional tradeoff: **Download Speed vs. Decompression Compute**.
1. **Network (Download):** A 4.7 MB file downloads in under 1 second on mobile networks, saving massive bandwidth costs and preventing users from bouncing while waiting for a 35 MB file to load.
2. **Client Compute (Decompression):** The browser's GPU cannot read Draco mathematics directly. When the webpage loads, it must use WebAssembly (WASM) to decompress the Draco blob back into raw floats before passing it to the graphics card. For a 30k vertex model, this WASM decompression takes under ~50 milliseconds.

Because network bottlenecks are always significantly slower than modern mobile CPUs, Draco provides a massive net performance win for web deployments.

*For details on how to deploy this compressed asset to the web, see [WEB_USAGE_GUIDE.md](./WEB_USAGE_GUIDE.md).*

### Critical Settings (Both Branches)

> ⚠️ **`bumpMapping.enable` and `displacementMapping.enable` must be `false`** in both Texturing nodes. Meshroom's GUI may silently reset these to `true` when re-saving the template. The generated EXR files are not used by STL or web viewers and waste processing time.

> ⚠️ **Unwrap Method must be `Basic`**. Both `LSCM` and `ABF` fail on AliceVision's generated geometry, producing black/untextured models. Do not change this.

## Known Issues

- **Meshroom 2025 ignores `--cache`** for custom pipelines — the script redirects `TMPDIR`/`TMP`/`TEMP` environment variables as a workaround.
- **LSCM/ABF unwrap methods crash** on both branches — use `Basic` only.
- **Bump/displacement maps reset to `true`** when editing the template in Meshroom's GUI — always verify after saving.
- **`DescriptionConflict`** if the Texturing node's `output` is set via `inputs` in JSON — the script resolves this by copying from the cache instead of attempting to overwrite the output path.