# Meshroom Photogrammetry Pipeline

Automated 3D model generation from photographs using [AliceVision/Meshroom](https://alicevision.org/), producing three distinct output variants simultaneously. The pipeline is containerized using Docker and is designed for deployment as a serverless API on the **RunPod** platform.

| Output | Format | Purpose | Typical Size |
|---|---|---|---|
| **High-poly model** | `.obj` + `.png` textures | Game development, VFX, detailed visualization | 150-300+ MB |
| **Printable model** | `.stl` | 3D printing (watertight geometry) | 50-100 MB |
| **Low-poly model** | `.glb` | Web applications & mobile viewers (compact binary format, easy to render) | 5-20 MB |

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
                                 ┌───────────────────┐  ┌─────────────┐
                                 │ OBJ → STL         │  │ OBJ → GLB   │
                                 │ (trimesh)         │  │ (trimesh)   │
                                 └───────────────────┘  └─────────────┘
                                           │                    │
                                           ▼                    ▼
                             Texturing_1/  printable_model.stl  web_model.glb
                      (High-poly OBJ + PNG)
```

The core orchestration is handled by Python (`main.py`):
1. **Pre-processing**: Downloads input photographs from a Cloudflare R2 bucket.
2. **Photogrammetry**: Runs `meshroom_batch` headless (no GUI) to process the images and generate the base geometry.
3. **Branching**:
   - The **High Branch** generates a detailed `.obj` with 4096px `.png` textures.
   - The **Low Branch** decimates the mesh and generates a lightweight `.obj` with 2048px `.jpg` textures.
4. **Post-processing**:
   - The High Branch `.obj` is provided as-is for game dev / VFX (`Texturing_1/`).
   - The High Branch `.obj` is additionally converted to a watertight `.stl` for 3D printing.
   - The Low Branch `.obj` is packed with its materials and `.jpg` textures into a single binary `.glb` file for web deployment (drastically reducing size).
5. **Delivery**: Zips the final assets and uploads them back to Cloudflare R2.

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

## Usage

### 1. Local Simulation

You can simulate the entire flow locally using `simulation.py`:

```bash
python simulation.py
```
This script will:
- Upload images from `input_images/` to R2.
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

## Pipeline Settings (template.mg)

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
| Keep Largest Mesh Only | true |
| Smoothing Iterations | 2 |
| Texture Side | 2048 |
| Downscale | 2 |
| Color Format | JPG (compressed) |
| Unwrap Method | Basic |

### Critical Settings (Both Branches)

> ⚠️ **`bumpMapping.enable` and `displacementMapping.enable` must be `false`** in both Texturing nodes. Meshroom's GUI may silently reset these to `true` when re-saving the template. The generated EXR files are not used by STL or web viewers and waste processing time.

> ⚠️ **Unwrap Method must be `Basic`**. Both `LSCM` and `ABF` fail on AliceVision's generated geometry, producing black/untextured models. Do not change this.

## Known Issues

- **Meshroom 2025 ignores `--cache`** for custom pipelines — the script redirects `TMPDIR`/`TMP`/`TEMP` environment variables as a workaround.
- **LSCM/ABF unwrap methods crash** on both branches — use `Basic` only.
- **Bump/displacement maps reset to `true`** when editing the template in Meshroom's GUI — always verify after saving.
- **`DescriptionConflict`** if the Texturing node's `output` is set via `inputs` in JSON — the script resolves this by copying from the cache instead of attempting to overwrite the output path.