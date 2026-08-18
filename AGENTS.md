# Project Context

This project automates a photogrammetry pipeline using the AliceVision engine (Meshroom) and a Python orchestration script. The system is designed to be deployed as a Dockerized Serverless API on the **RunPod** platform. It integrates with Cloudflare R2 for downloading input image datasets and uploading the final 3D model assets.

The pipeline processes standard images (no turntable, no AI background masks) and simultaneously generates three distinct versions of the same 3D model:

1. **High/HD Version**: A high-poly `.obj` with lossless `.png` textures for game development, VFX, and detailed visualization.
2. **Printable Version**: A watertight `.stl` extracted from the high-poly geometry for 3D printing.
3. **Low/Web Version**: A low-poly `.glb` (binary glTF) with compressed `.jpg` textures optimized for fast loading on web and mobile platforms.

---

# Meshroom Pipeline Architecture (`.mg` Template)

The base template excludes all AI segmentation nodes (`ImageDetectionPrompt`, `ImageSegmentationBox`), relying on classic background extraction for camera alignment.

The Meshroom graph forks after generating the base geometry (`MeshFiltering_1`).

## Core Branch

Images go through the standard processing chain:

```
CameraInit -> FeatureExtraction -> ImageMatching -> FeatureMatching
-> StructureFromMotion -> PrepareDenseScene -> DepthMap -> DepthMapFilter
-> Meshing -> MeshFiltering_1
```

## Branch 1: High/HD Model (Maximum Quality)

Connected directly from `MeshFiltering_1`.

**Texturing_1 settings:**
| Setting | Value | Notes |
|---|---|---|
| Texture Side | 4096 | High texture resolution (down from 8192 for stability/speed) |
| Downscale | 1 | Full resolution, no downscaling |
| Output Format | `.obj` | Left as-is for VFX/Gaming, and also converted to `.stl` |
| Color Mapping | PNG | Lossless texture format |
| Unwrap Method | **Basic** | Only stable method (see Known Issues) |
| useUDIM | false | Single texture tile, simpler to manage |
| bumpMapping | **false** | See Known Issues — must stay disabled |
| displacementMapping | **false** | See Known Issues — must stay disabled |

**Purpose**: Rich raw geometry with a very clear texture. Provided as an `.obj` + `.png` combination and additionally converted to `.stl` for 3D printing.

## Branch 2: Low/Web Model (Maximum Performance)

Connected from `MeshFiltering_1`, optimized to prevent mobile browser crashes due to limited VRAM.

**MeshDecimate_1 settings:**
| Setting | Value | Notes |
|---|---|---|
| Max Vertices | 50,000 | Produces ~100k polygons. Lower to 20k-30k if mobile is still slow |

**MeshFiltering_2 settings (post-decimate cleanup):**
| Setting | Value | Notes |
|---|---|---|
| Keep Only Largest Mesh | **true** | Removes micro-islands that cause unwrap errors |
| Smoothing Iterations | 2 | Relaxes topology without losing detail |

**Texturing_2 settings:**
| Setting | Value | Notes |
|---|---|---|
| Texture Side | 2048 | Optimal for mobile VRAM |
| Downscale | 2 | Good balance of detail vs processing speed |
| Output Format | `.obj` | Converted to `.glb` by the Python script |
| Color Mapping | JPG | Compressed, web-friendly |
| Unwrap Method | **Basic** | Only stable method (see Known Issues) |
| useUDIM | false | Single texture tile |
| bumpMapping | **false** | See Known Issues — must stay disabled |
| displacementMapping | **false** | See Known Issues — must stay disabled |

**Purpose**: Lightweight model for web viewers. The OBJ is converted to a single `.glb` file (binary glTF with embedded textures) by the Python script, typically achieving massive size reduction.

---

# Serverless Architecture & Python Script Role

The Python script (`main.py`) acts as the orchestration layer for the serverless endpoint. It runs headless (no GUI) and is containerized via Docker.

**Main tasks:**

1. **Environment Setup & Download**: Fetches the input image dataset from a specified Cloudflare R2 bucket (`download_files.py`).
2. **Pipeline Execution**: Prepares the `.mg` JSON template and launches `meshroom_batch` via CLI. It uses a `TMPDIR`/`TEMP` redirect so the cache stays inside the output directory (portable across Windows and Docker/Linux).
3. **Output Organization**: Identifies both Texturing branches in the cache (by texture file extension: PNG = High, JPG = Low) and copies them into organized subfolders (`Texturing_1/`, `Texturing_2/`).
4. **Post-Processing (High Branch)**: Uses `trimesh` to load the high-poly `.obj` and export a watertight `.stl` for 3D printing. The original `.obj` + `.png` are preserved.
5. **Post-Processing (Low Branch)**: Uses `trimesh` to pack the low-poly `.obj` + `.mtl` + JPG textures into a single `.glb` binary file.
6. **Upload & Cleanup**: Zips the final `Texturing_1/` assets, `printable_model.stl`, and `web_model.glb` into `output.zip`, uploads it back to Cloudflare R2 (`upload_files.py`), and cleans up intermediate files.

---

# Known Issues & Quirks

> **CRITICAL: `bumpMapping` and `displacementMapping` must be set to `false` in both Texturing nodes.**
>
> Meshroom's GUI tends to reset these to `true` when the template is re-saved. If left enabled, they generate large `.exr` normal/displacement map files that are:
> - Not used by STL (3D printing ignores textures)
> - Not used by web viewers (three.js / model-viewer don't import Meshroom's EXR maps)
> - A waste of processing time and disk space
>
> Always verify these are `false` after editing the template in Meshroom's GUI.

> **Unwrap Method: Only `Basic` works.**
>
> Both `LSCM` and `ABF` fail on both High and Low branches, producing either black/untextured models or crashing during UV unwrapping. This is an AliceVision implementation limitation with the geometry produced by its own pipeline. Do not change from `Basic`.

> **Meshroom 2025 ignores `--cache` for custom pipelines.**
>
> When using a custom `.mg` template via `--pipeline`, Meshroom writes cache to `%TEMP%/MeshroomCache` regardless of the `--cache` argument. The script works around this by redirecting `TMPDIR`/`TMP`/`TEMP` environment variables for the child process, forcing cache into the output directory.

> **Meshroom 2025 `DescriptionConflict` on Texturing output.**
>
> The Texturing node's `output` field cannot be overridden via `inputs` in the `.mg` JSON — doing so causes an `AssertionError` / `DescriptionConflict`. The script does not modify this field; instead, it copies results from the cache after execution.