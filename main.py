import json
import os
import re
import subprocess
import shutil
import sys
import tempfile
# pyrefly: ignore [missing-import]
import trimesh
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# CONSTANTS
# ==========================================
MESHROOM_EXE = (
    os.environ.get("MESHROOM_EXE")
    or shutil.which("meshroom_batch")
    or r"C:\path\to\Meshroom-2025.1.0\meshroom_batch.exe"
)


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def prepare_pipeline(template_path, temp_mg_path):
    """
    Reads the .mg JSON template and saves it as a temporary file.

    NOTE (Meshroom 2025): The Texturing node's 'output' field cannot be
    overridden via inputs (causes DescriptionConflict). Results are written
    to MeshroomCache and copied by this script afterward.
    """
    with open(template_path, "r", encoding="utf-8") as f:
        pipeline_data = json.load(f)

    texturing_nodes = []
    for node_name, node_data in pipeline_data.get("graph", {}).items():
        if node_data.get("nodeType") == "Texturing":
            texturing_nodes.append(node_name)
            print(f"  [CONFIG] Texturing node found: '{node_name}'")

    if not texturing_nodes:
        print("  [CONFIG] WARNING: No Texturing nodes found in template!")

    with open(temp_mg_path, "w", encoding="utf-8") as f:
        json.dump(pipeline_data, f, indent=4)

    return texturing_nodes


def find_texturing_cache_folders(cache_root):
    """
    Scans MeshroomCache/Texturing/ for folders containing texturedMesh.obj.

    Returns dict: { 'high': <path with PNG textures>, 'low': <path with JPG textures> }
    Branches are identified by their texture file extensions:
      - PNG textures -> High branch (full quality for printing)
      - JPG textures -> Low branch (compressed for web)
    """
    texturing_dir = os.path.join(cache_root, "Texturing")
    result = {"high": None, "low": None}

    if not os.path.exists(texturing_dir):
        return result

    for uid_folder in os.listdir(texturing_dir):
        folder_path = os.path.join(texturing_dir, uid_folder)
        if not os.path.isdir(folder_path):
            continue

        files = os.listdir(folder_path)
        if not any(f == "texturedMesh.obj" for f in files):
            continue

        has_png = any(f.lower().endswith(".png") for f in files)
        has_jpg = any(f.lower().endswith((".jpg", ".jpeg")) for f in files)

        if has_png and not has_jpg:
            result["high"] = folder_path
        elif has_jpg and not has_png:
            result["low"] = folder_path
        elif result["high"] is None:
            result["high"] = folder_path

    return result


def copy_texturing_output(cache_folder, dest_folder, label):
    """
    Copies all relevant files (OBJ, MTL, textures) from a Texturing
    cache folder into the destination folder.

    Returns the path to the copied texturedMesh.obj, or None on failure.
    """
    if not cache_folder or not os.path.exists(cache_folder):
        print(f"  [{label}] WARNING: Cache folder not found: {cache_folder}")
        return None

    os.makedirs(dest_folder, exist_ok=True)

    relevant_ext = {".obj", ".mtl", ".png", ".jpg", ".jpeg", ".gltf", ".glb"}
    obj_dest = None
    copied = []

    for fname in os.listdir(cache_folder):
        ext = os.path.splitext(fname)[1].lower()
        if ext in relevant_ext:
            shutil.copy2(
                os.path.join(cache_folder, fname),
                os.path.join(dest_folder, fname),
            )
            copied.append(fname)
            if fname == "texturedMesh.obj":
                obj_dest = os.path.join(dest_folder, fname)

    if copied:
        print(f"  [{label}] Copied {len(copied)} files to: {dest_folder}")
        for fname in sorted(copied):
            size_mb = os.path.getsize(os.path.join(dest_folder, fname)) / (1024 * 1024)
            print(f"           - {fname} ({size_mb:.1f} MB)")
    else:
        print(f"  [{label}] WARNING: Nothing to copy from {cache_folder}")

    return obj_dest


def convert_obj_to_stl(obj_path, stl_path):
    """Converts a high-poly OBJ mesh to a watertight STL for 3D printing."""
    try:
        print(f"\n  [STL] Processing geometry: {os.path.basename(obj_path)}...")
        mesh = trimesh.load(obj_path, force="mesh")
        if not mesh.is_watertight:
            trimesh.repair.fill_holes(mesh)
        mesh.export(stl_path)
        size_mb = os.path.getsize(stl_path) / (1024 * 1024)
        print(f"  [STL] Saved: {stl_path} ({size_mb:.1f} MB)")
    except Exception as e:
        print(f"  [STL] Conversion error: {e}")


def convert_obj_to_glb(obj_folder, glb_path):
    """
    Packs an OBJ + MTL + texture images into a single GLB (binary glTF).

    GLB stores geometry as compact binary buffers and embeds textures,
    resulting in a dramatically smaller file compared to text-based OBJ.
    Typical compression: 90 MB OBJ -> 5-8 MB GLB.
    """
    obj_path = os.path.join(obj_folder, "texturedMesh.obj")
    if not os.path.exists(obj_path):
        print(f"  [GLB] ERROR: OBJ not found: {obj_path}")
        return

    try:
        print(f"\n  [GLB] Converting OBJ -> GLB...")
        print(f"        Source: {obj_folder}")

        # Load as Scene to preserve materials and texture references.
        # trimesh resolves MTL + texture paths relative to the OBJ location.
        scene = trimesh.load(obj_path)

        # Export as binary glTF (.glb) — embeds geometry + textures in one file
        with open(glb_path, "wb") as f:
            f.write(scene.export(file_type="glb"))

        size_mb = os.path.getsize(glb_path) / (1024 * 1024)
        print(f"  [GLB] Saved: {glb_path} ({size_mb:.1f} MB)")

        # Show compression ratio vs source OBJ
        obj_size = os.path.getsize(obj_path) / (1024 * 1024)
        ratio = (1 - size_mb / obj_size) * 100 if obj_size > 0 else 0
        print(f"  [GLB] Compression: {obj_size:.1f} MB OBJ -> {size_mb:.1f} MB GLB ({ratio:.0f}% smaller)")

    except Exception as e:
        print(f"  [GLB] Conversion error: {e}")


# ==========================================
# MAIN PIPELINE
# ==========================================

def run_pipeline(input_images_dir, output_dir, template_path):
    """
    Orchestrates the full Meshroom photogrammetry pipeline:

      1. Prepares the pipeline template
      2. Runs meshroom_batch with TMPDIR redirect (keeps cache local)
      3. Copies results from cache into organized folders:
            output/Texturing_1/  <- High (OBJ + PNG textures)
            output/Texturing_2/  <- Low  (OBJ + JPG textures)
      4. Post-processing:
            - High branch -> STL for 3D printing
            - Low branch  -> GLB for web (single binary, embedded textures)
    """
    if not os.path.exists(input_images_dir):
        print(f"[ERROR] Input images folder not found: {input_images_dir}")
        return

    if not os.path.exists(MESHROOM_EXE):
        print(f"[ERROR] Meshroom executable not found: {MESHROOM_EXE}")
        return

    os.makedirs(output_dir, exist_ok=True)

    temp_mg_path   = os.path.join(output_dir, "pipeline_temp.mg")
    output_dir_abs = os.path.abspath(output_dir)
    cache_dir      = os.path.join(output_dir_abs, "MeshroomCache")
    # Fallback: default location where Meshroom writes when TMPDIR is not set
    sys_cache_dir  = os.path.join(tempfile.gettempdir(), "MeshroomCache")

    print(f"\n{'='*55}")
    print(f"  MESHROOM PIPELINE - INITIALIZATION")
    print(f"{'='*55}")
    print(f"  Input images: {os.path.abspath(input_images_dir)}")
    print(f"  Output dir:   {output_dir_abs}")

    # -- Step 1: Prepare template ----------------------------------------
    print(f"\n[1/4] Preparing pipeline template...")
    prepare_pipeline(template_path, temp_mg_path)

    # -- Step 2: Run Meshroom --------------------------------------------
    print(f"\n[2/4] Running Meshroom (this may take several minutes)...")
    command = [
        MESHROOM_EXE,
        "--pipeline", temp_mg_path,
        "--input",    os.path.abspath(input_images_dir),
        "--cache",    cache_dir,
        "--verbose",  "info",
    ]

    # Redirect the child process temp directory to our output folder.
    # Meshroom creates MeshroomCache inside the temp dir, so results
    # end up in cache_dir instead of %TEMP%. Works on Windows and Linux/Docker.
    child_env = os.environ.copy()
    child_env["TMPDIR"] = output_dir_abs   # Linux / macOS / Docker
    child_env["TMP"]    = output_dir_abs   # Windows
    child_env["TEMP"]   = output_dir_abs   # Windows

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
        )

        node_re = re.compile(r"\[(\d+)/(\d+)\] (\w+)")
        for line in process.stdout:
            line = line.rstrip()
            if not line:
                continue
            if node_re.search(line):
                print(f"  [MR] {line}")
            elif "already computed" in line or "chunk already" in line:
                print(f"  [MR] (cached) {line.split(':')[-1].strip()}")
            elif "error" in line.lower() or "warning" in line.lower():
                print(f"  [MR] {line}")

        process.wait()

        # Meshroom may return exit code 1 even on success with custom pipelines
        if process.returncode > 1:
            raise RuntimeError(f"Meshroom failed (exit code: {process.returncode})")

        print(f"\n  Meshroom finished (exit code: {process.returncode})")

    except Exception as e:
        print(f"\n[FATAL ERROR - Meshroom]: {e}")
        return
    finally:
        if os.path.exists(temp_mg_path):
            os.remove(temp_mg_path)

    # -- Step 3: Organize outputs ----------------------------------------
    print(f"\n[3/4] Organizing output files...")

    texturing_cache = {"high": None, "low": None}
    for loc in [cache_dir, sys_cache_dir]:
        found = find_texturing_cache_folders(loc)
        if found["high"] and not texturing_cache["high"]:
            texturing_cache["high"] = found["high"]
        if found["low"] and not texturing_cache["low"]:
            texturing_cache["low"] = found["low"]
        if texturing_cache["high"] and texturing_cache["low"]:
            break

    print(f"\n  High branch (PNG): {texturing_cache['high'] or 'NOT FOUND'}")
    print(f"  Low branch  (JPG): {texturing_cache['low']  or 'NOT FOUND'}")

    # Copy HIGH branch -> Texturing_1/
    print(f"\n  --- HIGH Branch (Texturing_1) ---")
    dest_high = os.path.join(output_dir_abs, "Texturing_1")
    obj_high = copy_texturing_output(texturing_cache["high"], dest_high, "HIGH")

    # Copy LOW branch -> Texturing_2/
    print(f"\n  --- LOW Branch (Texturing_2) ---")
    dest_low = os.path.join(output_dir_abs, "Texturing_2")
    obj_low = copy_texturing_output(texturing_cache["low"], dest_low, "LOW")

    # -- Step 4: Post-processing -----------------------------------------
    print(f"\n[4/4] Post-processing...")

    # High -> STL for 3D printing
    if obj_high:
        stl_path = os.path.join(output_dir_abs, "printable_model.stl")
        convert_obj_to_stl(obj_high, stl_path)

    # Low -> GLB for web (compact binary with embedded textures)
    if obj_low:
        glb_path = os.path.join(output_dir_abs, "web_model.glb")
        convert_obj_to_glb(dest_low, glb_path)

    # -- Summary report --------------------------------------------------
    print(f"\n{'='*55}")
    print(f"  PIPELINE COMPLETE - FILE SUMMARY")
    print(f"{'='*55}")

    for subfolder, label in [("Texturing_1", "High - OBJ + PNG"), ("Texturing_2", "Low - OBJ + JPG")]:
        path = os.path.join(output_dir_abs, subfolder)
        if os.path.exists(path) and os.listdir(path):
            files = [f for f in os.listdir(path) if not f.startswith(".")]
            print(f"\n  {subfolder}/ [{label}]")
            for f in sorted(files):
                size_mb = os.path.getsize(os.path.join(path, f)) / (1024 * 1024)
                print(f"    - {f} ({size_mb:.1f} MB)")
        else:
            print(f"\n  {subfolder}/ -> EMPTY or not found")

    # Show generated derivative files
    for fname in ["printable_model.stl", "web_model.glb"]:
        fpath = os.path.join(output_dir_abs, fname)
        if os.path.exists(fpath):
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            print(f"\n  {fname} ({size_mb:.1f} MB)")

    print(f"\n  All files in: {output_dir_abs}")
    print(f"{'='*55}\n")


# ==========================================
# CONFIGURATION & ENTRY POINT
# ==========================================
if __name__ == "__main__":
    INPUT_IMAGES = "./dataset_test/input_images"
    OUTPUT_DIR   = "./dataset_test/output"
    TEMPLATE_MG  = "./template.mg"

    run_pipeline(INPUT_IMAGES, OUTPUT_DIR, TEMPLATE_MG)
