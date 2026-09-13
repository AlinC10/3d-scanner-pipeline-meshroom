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

**Purpose**: Lightweight model for web viewers. The OBJ is converted to a single `.glb` file (binary glTF with embedded textures) by the Python script, typically achieving massive size reduction. The python script goes one step further by applying Draco geometry compression on the GLB to reduce size by an additional 80-90%.

## Operating Modes & Pipeline Templates

The script supports three distinct operating modes, which determine how images are passed into Meshroom:

1. **`single` Mode (Default)**: Uses `template.mg` for a standard, flat directory of images (e.g. from a drone or handheld camera).
2. **`rig` Mode**: Uses `template.mg` with an input directory structure consisting of `rig/0/` and `rig/1/`. Used for multi-camera captures (e.g., a turntable with 2 cameras separated by 30 degrees).
3. **`two-sides` Mode**: Uses `template_two_sides.mg`. Designed for scanning an object on a turntable, flipping it over, and scanning the bottom. It utilizes *two* separate `CameraInit` nodes which feed into an `SfMMerge` node.

---

# Serverless Architecture & Python Script Role

The Python script (`main.py`) acts as the orchestration layer for the serverless endpoint. It runs headless (no GUI) and is containerized via Docker.

**Main tasks:**

1. **Environment Setup & Download**: Fetches the input image dataset from a specified Cloudflare R2 bucket.
2. **Pipeline Execution**: 
   - Prepares the `.mg` JSON template.
   - **For `two-sides` mode**: Meshroom's CLI `--input` argument fundamentally does not support targeting multiple `CameraInit` nodes in the same graph. To bypass this limitation, the script manually executes `aliceVision_cameraInit` for each rig (producing `.sfm` files), reads the generated viewpoints and intrinsics, and directly injects them into the `.mg` JSON before launching Meshroom.
   - Launches `meshroom_batch`. It uses a `TMPDIR`/`TEMP` redirect so the cache stays inside the output directory (portable across Windows and Docker/Linux).
3. **Output Organization**: Identifies both Texturing branches in the cache (by texture file extension: PNG = High, JPG = Low) and copies them into organized subfolders (`Texturing_1/`, `Texturing_2/`).
4. **Post-Processing (Print Formats)**: Uses `trimesh` to load both high-poly and low-poly branches, run `trimesh.repair.fill_holes()`, and export watertight **`.stl`** and **`.3mf`** formats for 3D printing.
5. **Post-Processing (Web Formats)**: Uses `trimesh` to pack the OBJ + MTL + JPG textures into a single `.glb` binary file. It then runs a custom **Draco Compression** pass using `DracoPy` and `pygltflib`. The pass strips the raw floating-point geometry arrays from the GLB, replaces them with an arithmetic-compressed Draco blob (`KHR_draco_mesh_compression`), and dynamically reads the exact C++ attribute IDs assigned by DracoPy to prevent 3D viewers from cross-wiring UVs with 3D positions.
6. **Upload & Cleanup**: Packages the final outputs into `output.zip` containing `obj/`, `glb/`, `stl/`, and `3mf/` subfolders, uploads it back to Cloudflare R2, and cleans up intermediate files.

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