import json
import os
import re
import subprocess
import shutil
import tempfile
import gc
import trimesh
import runpod
import io
import time
import threading
import psutil
import atexit
from PIL import Image
import clouddlare_r2 as r2

# Draco compression support (optional — graceful fallback if not installed)
try:
    import DracoPy
    import struct
    import numpy as np
    from pygltflib import GLTF2
    _DRACO_AVAILABLE = True
except ImportError:
    _DRACO_AVAILABLE = False

def _monitor_memory():
    global _highest_ram, _mem_running
    _highest_ram = 0
    _mem_running = True
    seconds_passed = 0
    
    def print_final():
        global _mem_running
        _mem_running = False
        print(f"\n[MEMORY] Final Highest RAM + Swap Consumed: {_highest_ram:.2f} MB\n")
        
    atexit.register(print_final)
    
    while _mem_running:
        try:
            vmem = psutil.virtual_memory()
            smem = psutil.swap_memory()
            current_mb = (vmem.used + smem.used) / (1024 * 1024)
            
            if current_mb > _highest_ram:
                _highest_ram = current_mb
                
            seconds_passed += 1
            
            if seconds_passed % 10 == 0:
                print(f"[MEMORY] Current RAM + Swap Used: {current_mb:.2f} MB")
                
            if seconds_passed % 60 == 0:
                print(f"[MEMORY] Highest RAM + Swap Consumed so far: {_highest_ram:.2f} MB")
                
            time.sleep(1)
        except Exception:
            break

_mem_thread = threading.Thread(target=_monitor_memory, daemon=True)
_mem_thread.start()
# === CONSTANTS ===
from clouddlare_r2 import OUTPUT_DIR, INPUT_IMAGES, R2_PIPELINE_IMAGES_BUCKET
from config import MESHROOM_EXE, TEMPLATE_MG


# === UTILITY FUNCTIONS ===
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


def _apply_draco_compression(glb_path, draco_glb_path, compression_level=7, quantization_bits=14):
    """
    Reads a GLB produced by trimesh and re-encodes all mesh primitive
    geometry buffers using Draco compression (KHR_draco_mesh_compression).

    Correctly strips the original raw geometry bufferViews from the binary
    chunk and replaces them with compact Draco blobs. Non-geometry bufferViews
    (images/textures) are preserved unchanged.

    Returns True on success, False if compression was skipped/failed.
    """
    if not _DRACO_AVAILABLE:
        print("  [DRACO] DracoPy / pygltflib not installed — skipping compression.")
        return False

    try:
        import base64
        from pygltflib import BufferView

        gltf = GLTF2().load(glb_path)

        # ── raw binary from GLB BIN chunk ────────────────────────────────
        raw_bin = b""
        if hasattr(gltf, "_glb_data") and gltf._glb_data:
            raw_bin = gltf._glb_data
        elif gltf.buffers and getattr(gltf.buffers[0], "uri", None):
            uri = gltf.buffers[0].uri
            if uri.startswith("data:"):
                _, b64 = uri.split(",", 1)
                raw_bin = base64.b64decode(b64)

        # ── helpers ───────────────────────────────────────────────────────
        def _bv_bytes(bv_idx):
            bv  = gltf.bufferViews[bv_idx]
            off = bv.byteOffset or 0
            return raw_bin[off : off + bv.byteLength]

        _COMPONENT = {5120: np.int8,   5121: np.uint8,  5122: np.int16,
                      5123: np.uint16, 5125: np.uint32, 5126: np.float32}
        _ELEM_SIZE = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
                      "MAT2":   4, "MAT3": 9, "MAT4": 16}

        def _acc_to_array(acc_idx):
            acc   = gltf.accessors[acc_idx]
            raw   = _bv_bytes(acc.bufferView)
            dtype = _COMPONENT[acc.componentType]
            n     = _ELEM_SIZE[acc.type]
            off   = acc.byteOffset or 0
            arr   = np.frombuffer(raw[off:], dtype=dtype).copy()
            if n > 1:
                arr = arr.reshape(-1, n)
            return arr[:acc.count]

        # ── Pass 1: read geometry data and tag geometry bufferViews ──────
        geometry_bv_set = set()   # bufferView indices used by geometry
        prim_records    = []      # (mesh_i, prim_i, pos, faces, nrm, tex)

        for mi, mesh in enumerate(gltf.meshes):
            for pi, prim in enumerate(mesh.primitives):
                attrs = prim.attributes
                if attrs.POSITION is None:
                    continue

                # POSITION
                acc = gltf.accessors[attrs.POSITION]
                if acc.bufferView is not None:
                    geometry_bv_set.add(acc.bufferView)
                pos = _acc_to_array(attrs.POSITION).astype(np.float32)

                # INDICES
                faces = None
                if prim.indices is not None:
                    acc = gltf.accessors[prim.indices]
                    if acc.bufferView is not None:
                        geometry_bv_set.add(acc.bufferView)
                    faces = _acc_to_array(prim.indices).astype(np.uint32).flatten().reshape(-1, 3)

                # NORMAL
                nrm = None
                if attrs.NORMAL is not None:
                    acc = gltf.accessors[attrs.NORMAL]
                    if acc.bufferView is not None:
                        geometry_bv_set.add(acc.bufferView)
                    nrm = _acc_to_array(attrs.NORMAL).astype(np.float32)

                # TEXCOORD_0
                tex = None
                if attrs.TEXCOORD_0 is not None:
                    acc = gltf.accessors[attrs.TEXCOORD_0]
                    if acc.bufferView is not None:
                        geometry_bv_set.add(acc.bufferView)
                    tex = _acc_to_array(attrs.TEXCOORD_0).astype(np.float32)

                prim_records.append((mi, pi, pos, faces, nrm, tex))

        if not prim_records:
            print("  [DRACO] No compressible primitives found — skipping.")
            return False

        # ── Pass 2: null out geometry accessor bufferViews ───────────────
        # Per the KHR_draco_mesh_compression spec, geometry accessors must
        # have bufferView=None; the actual data comes from the Draco blob.
        for mi, pi, *_ in prim_records:
            prim  = gltf.meshes[mi].primitives[pi]
            attrs = prim.attributes
            for acc_idx in [attrs.POSITION, attrs.NORMAL, attrs.TEXCOORD_0, prim.indices]:
                if acc_idx is not None:
                    gltf.accessors[acc_idx].bufferView = None
                    gltf.accessors[acc_idx].byteOffset = 0

        # ── Pass 3: encode each primitive with DracoPy ───────────────────
        draco_records = []   # (mi, pi, draco_bytes)
        for mi, pi, pos, faces, nrm, tex in prim_records:
            kwargs = dict(
                points              = pos,
                faces               = faces,
                quantization_bits   = quantization_bits,
                compression_level   = compression_level,
                quantization_range  = -1,
                quantization_origin = None,
                create_metadata     = False,
                preserve_order      = False,
            )
            if nrm is not None:
                kwargs["normals"] = nrm
            if tex is not None:
                kwargs["tex_coord"] = tex
            draco_records.append((mi, pi, bytes(DracoPy.encode(**kwargs))))

        # ── Pass 4: rebuild binary blob (drop geometry, keep images) ─────
        def _align4(b: bytes) -> bytes:
            rem = len(b) % 4
            return b + b"\x00" * (4 - rem) if rem else b

        kept_indices  = [i for i in range(len(gltf.bufferViews))
                         if i not in geometry_bv_set]
        old_to_new_bv = {}
        new_bvs       = []
        new_bin       = b""

        for new_i, old_i in enumerate(kept_indices):
            old_bv = gltf.bufferViews[old_i]
            blob   = _bv_bytes(old_i)
            old_to_new_bv[old_i] = new_i

            nbv            = BufferView()
            nbv.buffer     = 0
            nbv.byteOffset = len(new_bin)
            nbv.byteLength = old_bv.byteLength
            if getattr(old_bv, "target", None):
                nbv.target = old_bv.target
            new_bvs.append(nbv)
            new_bin += _align4(blob)

        # Append Draco blobs
        draco_bv_map = {}   # (mi, pi) -> new BV index
        for mi, pi, draco_bytes in draco_records:
            bv_idx               = len(new_bvs)
            draco_bv_map[(mi, pi)] = bv_idx

            nbv             = BufferView()
            nbv.buffer      = 0
            nbv.byteOffset  = len(new_bin)
            nbv.byteLength  = len(draco_bytes)
            new_bvs.append(nbv)
            new_bin += _align4(draco_bytes)

        # ── Pass 5: remap accessor & image bufferView indices ─────────────
        for acc in gltf.accessors:
            if acc.bufferView is not None:
                acc.bufferView = old_to_new_bv.get(acc.bufferView, None)

        for img in (gltf.images or []):
            if getattr(img, "bufferView", None) is not None:
                img.bufferView = old_to_new_bv.get(img.bufferView, None)

        # ── Pass 6: attach Draco extension to each primitive ─────────────
        for mi, pi, _ in draco_records:
            prim  = gltf.meshes[mi].primitives[pi]
            attrs = prim.attributes
            attr_ids, counter = {}, 0
            attr_ids["POSITION"] = counter; counter += 1
            if attrs.NORMAL     is not None: attr_ids["NORMAL"]     = counter; counter += 1
            if attrs.TEXCOORD_0 is not None: attr_ids["TEXCOORD_0"] = counter; counter += 1

            if prim.extensions is None:
                prim.extensions = {}
            prim.extensions["KHR_draco_mesh_compression"] = {
                "bufferView": draco_bv_map[(mi, pi)],
                "attributes": attr_ids,
            }

        # ── Finalize & save ───────────────────────────────────────────────
        gltf.bufferViews = new_bvs
        gltf.buffers[0].byteLength = len(new_bin)

        if gltf.extensionsUsed is None:
            gltf.extensionsUsed = []
        if "KHR_draco_mesh_compression" not in gltf.extensionsUsed:
            gltf.extensionsUsed.append("KHR_draco_mesh_compression")
        if gltf.extensionsRequired is None:
            gltf.extensionsRequired = []
        if "KHR_draco_mesh_compression" not in gltf.extensionsRequired:
            gltf.extensionsRequired.append("KHR_draco_mesh_compression")

        gltf._glb_data = new_bin
        gltf.save_binary(draco_glb_path)

        before_mb = os.path.getsize(glb_path)       / (1024 * 1024)
        after_mb  = os.path.getsize(draco_glb_path) / (1024 * 1024)
        ratio     = (1 - after_mb / before_mb) * 100 if before_mb > 0 else 0
        print(f"  [DRACO] {before_mb:.1f} MB -> {after_mb:.1f} MB ({ratio:.0f}% smaller)")
        return True

    except Exception as e:
        print(f"  [DRACO] Compression failed: {e}")
        return False


def convert_obj_to_glb(obj_folder, glb_path, compress_textures=True,
                       draco=True, draco_level=7, draco_bits=14):
    """
    Packs an OBJ + MTL + texture images into a single GLB (binary glTF).

    Stage 1 (trimesh): loads the OBJ, optionally re-encodes textures as JPG
    in-memory, then writes a standard GLB.

    Stage 2 (Draco, optional): if `draco=True` and DracoPy+pygltflib are
    installed, re-encodes the mesh geometry buffers with Draco compression
    (KHR_draco_mesh_compression), shrinking geometry by ~80-95%.
    If Draco compression fails, the Stage 1 GLB is kept as-is.
    """

    obj_path = os.path.join(obj_folder, "texturedMesh.obj")
    if not os.path.exists(obj_path):
        print(f"  [GLB] ERROR: OBJ not found: {obj_path}")
        return

    try:
        print(f"\n  [GLB] Converting OBJ -> GLB (compress_textures={compress_textures})...")
        print(f"        Source: {obj_folder}")

        scene = trimesh.load(obj_path, process=False, force="scene")

        if hasattr(scene, "geometry"):
            has_materials = any(
                getattr(geom, "visual", None) is not None
                and hasattr(geom.visual, "material")
                and geom.visual.material is not None
                for geom in scene.geometry.values()
            )
            if not has_materials:
                print("  [GLB] WARNING: No materials detected after load — "
                      "check that the .mtl file and textures are present "
                      "in the same folder as the OBJ.")

            if compress_textures:
                for geom in scene.geometry.values():
                    if hasattr(geom.visual, "material"):
                        mat = geom.visual.material

                        # For OBJ, trimesh uses SimpleMaterial which uses the 'image' attribute
                        if hasattr(mat, 'image') and mat.image is not None:
                            img = mat.image
                            if img.mode != 'RGB':
                                img = img.convert('RGB')

                            buffer = io.BytesIO()
                            img.save(buffer, format="JPEG", quality=85)
                            buffer.seek(0)
                            mat.image = Image.open(buffer)
                            mat.image._meshroom_buffer = buffer  # Keep buffer alive!

                        # Also check for baseColorTexture (PBRMaterial format) just in case
                        if hasattr(mat, 'baseColorTexture') and mat.baseColorTexture is not None:
                            img = mat.baseColorTexture
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            buffer = io.BytesIO()
                            img.save(buffer, format="JPEG", quality=85)
                            buffer.seek(0)
                            mat.baseColorTexture = Image.open(buffer)
                            mat.baseColorTexture._meshroom_buffer = buffer  # Keep buffer alive!

        # ── Stage 1: export standard GLB via trimesh ─────────────────────
        with open(glb_path, "wb") as f:
            f.write(scene.export(file_type="glb"))

        size_mb  = os.path.getsize(glb_path) / (1024 * 1024)
        obj_size = os.path.getsize(obj_path)  / (1024 * 1024)
        ratio    = (1 - size_mb / obj_size) * 100 if obj_size > 0 else 0
        print(f"  [GLB] Stage 1 saved: {glb_path} ({size_mb:.1f} MB)")
        print(f"  [GLB] {obj_size:.1f} MB OBJ -> {size_mb:.1f} MB GLB ({ratio:.0f}% smaller)")

        # ── Stage 2: Draco geometry compression ──────────────────────────
        if draco and _DRACO_AVAILABLE:
            draco_path = glb_path.replace(".glb", "_draco.glb")
            print(f"\n  [GLB] Stage 2: applying Draco compression "
                  f"(level={draco_level}, bits={draco_bits})...")
            success = _apply_draco_compression(
                glb_path, draco_path,
                compression_level=draco_level,
                quantization_bits=draco_bits,
            )
            if success:
                # Replace the plain GLB with the Draco-compressed version
                os.replace(draco_path, glb_path)
                final_mb = os.path.getsize(glb_path) / (1024 * 1024)
                print(f"  [GLB] Final (Draco): {glb_path} ({final_mb:.1f} MB)")
            else:
                print("  [GLB] Draco stage skipped — keeping Stage 1 GLB.")
        elif draco and not _DRACO_AVAILABLE:
            print("  [GLB] Draco requested but DracoPy/pygltflib not installed "
                  "— add them to requirements.txt. Keeping Stage 1 GLB.")

    except Exception as e:
        print(f"  [GLB] Conversion error: {e}")



# === MAIN PIPELINE ===

def run_pipeline(job):
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
    runpod.serverless.progress_update(job, {
        "status": "PIPELINE CONFIGURATION",
        "progress": 0
    })

    if not os.path.exists(MESHROOM_EXE):
        print(f"[ERROR] Meshroom executable not found: {MESHROOM_EXE}")
        raise Exception("Meshroom executable not found")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    temp_mg_path   = os.path.join(OUTPUT_DIR, "pipeline_temp.mg")
    output_dir_abs = os.path.abspath(OUTPUT_DIR)
    cache_dir      = os.path.join(output_dir_abs, "MeshroomCache")
    # Fallback: default location where Meshroom writes when TMPDIR is not set
    sys_cache_dir  = os.path.join(tempfile.gettempdir(), "MeshroomCache")
    input_images_abs_dir = os.path.abspath(INPUT_IMAGES)
    
    print(f"\n{'='*55}")
    print(f"  MESHROOM PIPELINE - INITIALIZATION")
    print(f"{'='*55}")
    print(f"  Input images: {input_images_abs_dir}")
    print(f"  Output dir:   {output_dir_abs}")

    # -- Step 1: Prepare template ----------------------------------------
    print(f"\n[1/4] Preparing pipeline template...")
    prepare_pipeline(TEMPLATE_MG, temp_mg_path)


    # Download Images from R2
    if not MESHROOM_EXE.startswith("D:"):
        runpod.serverless.progress_update(job, {
            "status": "Downloading images...",
            "progress": 20
        })
        r2.download_every_img_from_bucket(INPUT_IMAGES, R2_PIPELINE_IMAGES_BUCKET)


    # -- Step 2: Run Meshroom --------------------------------------------
    print(f"\n[2/4] Running Meshroom (this may take several minutes)...")

    runpod.serverless.progress_update(job, {
        "status": "Running Meshroom (this may take several minutes)...",
        "progress": 40
    })
    
    command = [
        MESHROOM_EXE,
        "--pipeline", temp_mg_path,
        "--input",    input_images_abs_dir,
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
        raise
    finally:
        if os.path.exists(temp_mg_path):
            os.remove(temp_mg_path)

    # -- Step 3: Organize outputs ----------------------------------------
    print(f"\n[3/4] Organizing output files...")

    runpod.serverless.progress_update(job, {
        "status": "Organizing output files...",
        "progress": 60
    })

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
    runpod.serverless.progress_update(job, {
        "status": "Post-processing...",
        "progress": 80
    })

    gc.collect()

    # High -> STL & GLB
    if obj_high:
        high_stl_path = os.path.join(output_dir_abs, "high_model.stl")
        convert_obj_to_stl(obj_high, high_stl_path)
        gc.collect()
        
        # High -> GLB for viewing with compressed JPGs
        high_glb_path = os.path.join(output_dir_abs, "high_model.glb")
        convert_obj_to_glb(dest_high, high_glb_path, compress_textures=True, draco=False)
        gc.collect()

    # Low -> STL & GLB
    if obj_low:
        low_stl_path = os.path.join(output_dir_abs, "low_model.stl")
        convert_obj_to_stl(obj_low, low_stl_path)
        gc.collect()

        glb_path = os.path.join(output_dir_abs, "low_model.glb")
        convert_obj_to_glb(dest_low, glb_path, compress_textures=True, draco=True, draco_level=10, draco_bits=12)
        gc.collect()

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
    for fname in ["high_model.stl", "low_model.stl", "high_model.glb", "low_model.glb"]:
        fpath = os.path.join(output_dir_abs, fname)
        if os.path.exists(fpath):
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            print(f"\n  {fname} ({size_mb:.1f} MB)")

    print(f"\n  All files in: {output_dir_abs}")
    print(f"{'='*55}\n")

    if not MESHROOM_EXE.startswith("D:"):
        runpod.serverless.progress_update(job, {
            "status": "Upload generated files from server...",
            "progress": 100
        })

        r2.upload_generated_obj(OUTPUT_DIR)
    
        r2.delete_all_files_from_bucket()

    return {
        "status": "success"
    }


# === CONFIGURATION & ENTRY POINT ===
if __name__ == "__main__":
    # testing only (fake job)
    dummy_job = {"id": "test_local", "input": {}}
    run_pipeline(dummy_job)