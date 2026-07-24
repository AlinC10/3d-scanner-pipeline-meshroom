# Meshroom Photogrammetry Pipeline

Automated 3D model generation from photographs using [AliceVision/Meshroom](https://alicevision.org/), producing two output variants simultaneously:

| Output | Format | Purpose | Typical Size |
|---|---|---|---|
| **High-poly model** | `.stl` | 3D printing | 50-100 MB |
| **Low-poly model** | `.glb` | Web/mobile viewers | 5-20 MB |

## How It Works

```
Input Images (JPG/PNG)
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
│                                    (High: 8192px PNG)        │
│                                          │             MeshFiltering_2
│                                          │                    │
│                                          │             Texturing_2
│                                          │             (Low: 2048px JPG)
└──────────────────────────────────────────┼────────────────────┘
                                           │                    │
                                           ▼                    ▼
                                    ┌─────────────┐     ┌─────────────┐
                                    │ OBJ → STL   │     │ OBJ → GLB   │
                                    │ (trimesh)    │     │ (trimesh)    │
                                    └─────────────┘     └─────────────┘
                                           │                    │
                                           ▼                    ▼
                                   printable_model.stl    web_model.glb
```

The Python script (`main.py`) orchestrates everything:
1. Prepares the Meshroom template
2. Runs `meshroom_batch` headless (no GUI)
3. Collects results from cache into organized folders
4. Converts High branch OBJ → STL (for 3D printing)
5. Converts Low branch OBJ → GLB (for web, ~77% smaller than OBJ)

## Prerequisites

- **Meshroom 2025.1.0** — [Download](https://alicevision.org/#meshroom)
- **Python 3.10+** with a virtual environment
- **CUDA-capable GPU** (required by AliceVision for depth map computation)

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

### Configure Meshroom Path

Create a `.env` file in the project root directory and set the path to your `meshroom_batch` executable:

```env
MESHROOM_EXE=C:\path\to\Meshroom-2025.1.0\meshroom_batch.exe
```

If `meshroom_batch` is already in your system `PATH`, this step is optional (the script will find it automatically). You can also use `.env.example` as a template.

## Usage

### 1. Place Your Images

Put your input photographs in the `dataset_test/input_images/` folder.

For best results:
- Use 20-100 images covering all angles of the object
- Consistent lighting, no flash
- Overlap between consecutive shots (~60-80%)
- Avoid reflective/transparent surfaces

### 2. Run the Pipeline

```bash
python main.py
```

### 3. Collect Results

Results are written to `dataset_test/output/`:

```
dataset_test/output/
├── Texturing_1/            ← High-poly (OBJ + PNG texture)
├── Texturing_2/            ← Low-poly  (OBJ + JPG textures)
├── printable_model.stl     ← Ready for 3D printing
├── web_model.glb           ← Ready for web (single file, embedded textures)
└── MeshroomCache/          ← Intermediate cache (can be deleted)
```

## Project Structure

```
meshroom_test/
├── main.py              # Pipeline orchestration script
├── template.mg          # Meshroom pipeline template (JSON graph)
├── requirements.txt     # Python dependencies
├── AGENTS.md            # AI agent instructions & project context
├── .gitignore
└── dataset_test/
    ├── input_images/    # Source photographs (gitignored)
    └── output/          # Generated results (gitignored)
```

## Pipeline Settings (template.mg)

### High Branch (Texturing_1)

| Setting | Value |
|---|---|
| Texture Side | 8192 |
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

## Docker Support

The script is designed to be Docker-portable with minimal changes. It redirects `TMPDIR`/`TMP`/`TEMP` environment variables so Meshroom writes its cache inside the output directory instead of the system temp folder. On Linux/Docker, only `MESHROOM_EXE` path needs updating.

```python
# Docker example paths
INPUT_IMAGES = "/data/input_images"
OUTPUT_DIR   = "/data/output"
TEMPLATE_MG  = "/app/template.mg"
```

## Known Issues

- **Meshroom 2025 ignores `--cache`** for custom pipelines — the `TMPDIR` redirect is the workaround.
- **LSCM/ABF unwrap methods crash** on both branches — use `Basic` only.
- **Bump/displacement maps reset to `true`** when editing the template in Meshroom's GUI — always verify after saving.
- **`DescriptionConflict`** if the Texturing node's `output` is set via `inputs` in JSON — the script does not modify this field.

## License

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

