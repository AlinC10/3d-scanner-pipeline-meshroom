# Project Context

This project automates a photogrammetry pipeline using the AliceVision engine (Meshroom) and a Python orchestration script. The main goal is to process a set of standard images (no turntable, no AI background masks in this iteration) and simultaneously generate two versions of the same 3D model:

- **High/HD Version**: For 3D printing (STL export) or detailed visualization (LOD High).
- **Low/Web Version**: For fast loading on a web platform (LOD Low, GLB export).

---

# Meshroom Pipeline Architecture (`.mg` Template)

The base template excludes all AI segmentation nodes (`ImageDetectionPrompt`, `ImageSegmentationBox`), relying on classic background extraction for camera alignment.

The Meshroom graph forks after generating the base geometry (MeshFiltering_1).

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
| Texture Side | 8192 | Maximum texture resolution |
| Downscale | 1 | Full resolution, no downscaling |
| Output Format | `.obj` | Converted to `.stl` by the Python script |
| Color Mapping | PNG | Lossless texture format |
| Unwrap Method | **Basic** | Only stable method (see Known Issues) |
| useUDIM | false | Single texture tile, simpler to manage |
| bumpMapping | **false** | See Known Issues — must stay disabled |
| displacementMapping | **false** | See Known Issues — must stay disabled |

**Purpose**: Rich raw geometry (~100k+ polygons) with a very clear texture. Large file size (15-30+ MB), used only on explicit user request or for 3D printing.

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

**Purpose**: Lightweight model for web viewers. The OBJ is converted to a single `.glb` file (binary glTF with embedded textures) by the Python script, typically achieving ~77% size reduction (e.g., 88 MB OBJ → 20 MB GLB).

---

# Python Script Role

The Python script (`main.py`) is the orchestration layer that runs the pipeline headless (no GUI). It does not rely on Meshroom's visual interface.

**Main tasks:**

1. **Environment Setup**: Receives paths to the image dataset and the JSON template (`.mg`).

2. **Pipeline Execution**: Launches `meshroom_batch` via CLI with a `TMPDIR`/`TEMP` redirect so the cache stays inside the output directory (portable across Windows and Docker/Linux).

3. **Output Organization**: After Meshroom finishes, identifies both Texturing branches in the cache (by texture file extension: PNG = High, JPG = Low) and copies them into organized subfolders (`Texturing_1/`, `Texturing_2/`).

4. **Post-Processing (High Branch)**: Loads the high-poly `.obj` and exports a watertight `.stl` for 3D printing using `trimesh`.

5. **Post-Processing (Low Branch)**: Packs the low-poly `.obj` + `.mtl` + JPG textures into a single `.glb` (binary glTF) using `trimesh`. This embeds all textures into one compact binary file, ready for web deployment.

6. **Cleanup** *(planned)*: Delete the massive `MeshroomCache` folder after a successful run to free storage.

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