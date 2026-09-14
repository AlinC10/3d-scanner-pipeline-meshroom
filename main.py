import json
import os
import re
import subprocess
import shutil
import tempfile
import gc
import trimesh
def progress_update(job, status_dict):
    """
    Updates the progress of the job.
    :param job: The job object.
    :type job: dict
    :param status_dict: The status dictionary.
    :type status_dict: dict
    :return: None
    :rtype: None
    """
    print(f"[PROGRESS] {status_dict}")
import io
import time
import threading
import psutil
import atexit
from PIL import Image
import cloudflare_r2 as r2

# Draco compression support (optional — graceful fallback if not installed)
try:
    import DracoPy
    import numpy as np
    _DRACO_AVAILABLE = True
except ImportError:
    _DRACO_AVAILABLE = False

def _monitor_memory():
    """
    Monitors RAM and swap memory usage in a separate thread.
    :return: None
    :rtype: None
    """
    global _highest_ram, _mem_running
    _highest_ram = 0
    _mem_running = True
    seconds_passed = 0
    
    def print_final():
        """
        Prints the final highest memory consumed and stops monitoring.
        
        :return: None
        :rtype: None
        """
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
from cloudflare_r2 import OUTPUT_DIR, INPUT_IMAGES, RIG_IMAGES, TWO_SIDES_RIG1, TWO_SIDES_RIG2, R2_PIPELINE_IMAGES_BUCKET
from config import *


# === UTILITY FUNCTIONS ===
def prepare_pipeline(template_path, temp_mg_path):
    """
    Reads the .mg JSON template and saves it as a temporary file.

    NOTE (Meshroom 2025): The Texturing node's 'output' field cannot be
    overridden via inputs (causes DescriptionConflict). Results are written
    to MeshroomCache and copied by this script afterward.
    
    :param template_path: Path to the input .mg template file.
    :type template_path: str
    :param temp_mg_path: Path where the temporary .mg file will be saved.
    :type temp_mg_path: str
    :return: List of Texturing node names found in the template.
    :rtype: list
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
      
    :param cache_root: Path to the MeshroomCache root directory.
    :type cache_root: str
    :return: Dictionary containing paths to the high and low texturing cache folders.
    :rtype: dict
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
    
    :param cache_folder: Path to the source cache folder.
    :type cache_folder: str
    :param dest_folder: Path to the destination folder.
    :type dest_folder: str
    :param label: Label for logging purposes.
    :type label: str
    :return: Path to the copied texturedMesh.obj, or None on failure.
    :rtype: str or None
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


def convert_obj_to_print_formats(obj_path, stl_path, mf_path):
    """
    Converts a high-poly OBJ mesh to watertight STL and 3MF formats for 3D printing.
    
    :param obj_path: Path to the input OBJ file.
    :type obj_path: str
    :param stl_path: Path where the output STL file will be saved.
    :type stl_path: str
    :param mf_path: Path where the output 3MF file will be saved.
    :type mf_path: str
    :return: None
    :rtype: None
    """
    try:
        print(f"\n  [PRINT] Processing geometry: {os.path.basename(obj_path)}...")
        mesh = trimesh.load(obj_path, force="mesh")
        if not mesh.is_watertight:
            print("  [PRINT] Filling holes to make mesh watertight...")
            trimesh.repair.fill_holes(mesh)
        
        # Export STL
        mesh.export(stl_path)
        size_stl = os.path.getsize(stl_path) / (1024 * 1024)
        print(f"  [STL] Saved: {stl_path} ({size_stl:.1f} MB)")
        
        # Export 3MF
        mesh.export(mf_path)
        size_mf = os.path.getsize(mf_path) / (1024 * 1024)
        print(f"  [3MF] Saved: {mf_path} ({size_mf:.1f} MB)")
        
    except Exception as e:
        print(f"  [PRINT] Conversion error: {e}")


def _apply_draco_compression(glb_path, draco_glb_path, compression_level=7, quantization_bits=14):
    """
    Reads a GLB produced by trimesh and re-encodes all mesh primitive
    geometry buffers using Draco compression (KHR_draco_mesh_compression).
    
    :param glb_path: Path to the input GLB file.
    :type glb_path: str
    :param draco_glb_path: Path where the output Draco compressed GLB will be saved.
    :type draco_glb_path: str
    :param compression_level: Draco compression level (0-10).
    :type compression_level: int
    :param quantization_bits: Number of bits for Draco quantization.
    :type quantization_bits: int
    :return: True if compression was successful, False otherwise.
    :rtype: bool
    """
    if not _DRACO_AVAILABLE:
        print("  [DRACO] DracoPy not installed — skipping compression.")
        return False

    try:
        import base64
        from pygltflib import GLTF2, BufferView

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
            """
            Gets bytes of a buffer view.
            :param bv_idx: Index of the buffer view.
            :type bv_idx: int
            :return: Bytes of the buffer view.
            :rtype: bytes
            """
            bv  = gltf.bufferViews[bv_idx]
            off = bv.byteOffset or 0
            return raw_bin[off : off + bv.byteLength]

        _COMPONENT = {5120: np.int8,   5121: np.uint8,  5122: np.int16,
                      5123: np.uint16, 5125: np.uint32, 5126: np.float32}
        _ELEM_SIZE = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
                      "MAT2":   4, "MAT3": 9, "MAT4": 16}

        def _acc_to_array(acc_idx):
            """
            Converts an accessor to a numpy array.
            :param acc_idx: Index of the accessor.
            :type acc_idx: int
            :return: Numpy array containing accessor data.
            :rtype: numpy.ndarray
            """
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

                acc = gltf.accessors[attrs.POSITION]
                if acc.bufferView is not None: geometry_bv_set.add(acc.bufferView)
                pos = _acc_to_array(attrs.POSITION).astype(np.float32)

                faces = None
                if prim.indices is not None:
                    acc = gltf.accessors[prim.indices]
                    if acc.bufferView is not None: geometry_bv_set.add(acc.bufferView)
                    faces = _acc_to_array(prim.indices).astype(np.uint32).flatten().reshape(-1, 3)

                nrm = None
                if attrs.NORMAL is not None:
                    acc = gltf.accessors[attrs.NORMAL]
                    if acc.bufferView is not None: geometry_bv_set.add(acc.bufferView)
                    nrm = _acc_to_array(attrs.NORMAL).astype(np.float32)

                tex = None
                if attrs.TEXCOORD_0 is not None:
                    acc = gltf.accessors[attrs.TEXCOORD_0]
                    if acc.bufferView is not None: geometry_bv_set.add(acc.bufferView)
                    tex = _acc_to_array(attrs.TEXCOORD_0).astype(np.float32)

                prim_records.append((mi, pi, pos, faces, nrm, tex))

        if not prim_records:
            return False

        # ── Pass 2: null out geometry accessor bufferViews ───────────────
        for mi, pi, *_ in prim_records:
            prim  = gltf.meshes[mi].primitives[pi]
            attrs = prim.attributes
            for acc_idx in [attrs.POSITION, attrs.NORMAL, attrs.TEXCOORD_0, prim.indices]:
                if acc_idx is not None:
                    gltf.accessors[acc_idx].bufferView = None
                    gltf.accessors[acc_idx].byteOffset = 0

        # ── Pass 3: encode each primitive with DracoPy and extract IDs ───
        draco_records = []   # (mi, pi, draco_bytes, attr_ids)
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
                kwargs["normals"] = nrm.astype(np.float64)
            if tex is not None:
                kwargs["tex_coord"] = tex.astype(np.float64)
                
            draco_bytes = bytes(DracoPy.encode(**kwargs))
            
            # Decode briefly to read the unique IDs Draco automatically assigned
            # Draco geometry attribute types: POSITION=0, NORMAL=1, TEX_COORD=3
            decoded = DracoPy.decode(draco_bytes)
            attr_ids = {}
            for attr in decoded.attributes:
                if attr['attribute_type'] == 0:
                    attr_ids["POSITION"] = attr['unique_id']
                elif attr['attribute_type'] == 1:
                    attr_ids["NORMAL"] = attr['unique_id']
                elif attr['attribute_type'] == 3:
                    attr_ids["TEXCOORD_0"] = attr['unique_id']
                    
            draco_records.append((mi, pi, draco_bytes, attr_ids))

        # ── Pass 4: rebuild binary blob (drop geometry, keep images) ─────
        def _align4(b: bytes) -> bytes:
            """
            Aligns bytes to a 4-byte boundary.
            
            :param b: Input bytes.
            :type b: bytes
            :return: Aligned bytes.
            :rtype: bytes
            """
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
        for mi, pi, draco_bytes, _ in draco_records:
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
        for mi, pi, _, attr_ids in draco_records:
            prim  = gltf.meshes[mi].primitives[pi]
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

    Stage 1 (trimesh): loads the OBJ, optionally re-encodes textures as JPG.
    Stage 2 (Draco, optional): re-encodes mesh geometry buffers with Draco.
    
    :param obj_folder: Path to the folder containing the OBJ, MTL, and textures.
    :type obj_folder: str
    :param glb_path: Path where the output GLB file will be saved.
    :type glb_path: str
    :param compress_textures: Whether to compress textures to JPG.
    :type compress_textures: bool
    :param draco: Whether to apply Draco compression.
    :type draco: bool
    :param draco_level: Draco compression level.
    :type draco_level: int
    :param draco_bits: Number of bits for Draco quantization.
    :type draco_bits: int
    :return: None
    :rtype: None
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
            if compress_textures:
                for geom in scene.geometry.values():
                    if hasattr(geom.visual, "material"):
                        mat = geom.visual.material
                        for attr_name in ['image', 'baseColorTexture']:
                            if hasattr(mat, attr_name) and getattr(mat, attr_name) is not None:
                                img = getattr(mat, attr_name)
                                if img.mode != 'RGB':
                                    img = img.convert('RGB')
                                buffer = io.BytesIO()
                                img.save(buffer, format="JPEG", quality=85)
                                buffer.seek(0)
                                setattr(mat, attr_name, Image.open(buffer))
                                getattr(mat, attr_name)._meshroom_buffer = buffer

        # Export standard GLB via trimesh
        with open(glb_path, "wb") as f:
            f.write(scene.export(file_type="glb"))

        size_mb  = os.path.getsize(glb_path) / (1024 * 1024)
        obj_size = os.path.getsize(obj_path)  / (1024 * 1024)
        ratio    = (1 - size_mb / obj_size) * 100 if obj_size > 0 else 0
        print(f"  [GLB] Saved standard GLB: {glb_path} ({size_mb:.1f} MB)")

        # Apply Draco compression if requested
        if draco and _DRACO_AVAILABLE:
            draco_path = glb_path.replace(".glb", "_draco.glb")
            success = _apply_draco_compression(glb_path, draco_path, draco_level, draco_bits)
            if success:
                os.replace(draco_path, glb_path)
                print(f"  [GLB] Replaced with Draco compressed GLB.")
            else:
                print("  [GLB] Draco stage skipped/failed — keeping standard GLB.")

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
            
    :param job: Dictionary containing job configuration and inputs.
    :type job: dict
    :return: Dictionary containing the status of the pipeline run.
    :rtype: dict
    """
    progress_update(job, {
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
    # -- Determine input mode -----------------------------------------------
    # Accepted values: "single" (default, flat input_images/ folder)
    #                  "rig"    (input_images/rig/0/ + input_images/rig/1/)
    #                  "two-sides" (input_images/rig1/ + input_images/rig2/, dual CameraInit)
    # When submitting a RunPod job, pass: {"input": {"mode": "rig"}} or {"input": {"mode": "two-sides"}}
    mode = job.get("input", {}).get("mode", "single").strip().lower()
    rig_mode = (mode == "rig")
    two_sides_mode = (mode == "two-sides")

    # Select the correct template based on mode
    if two_sides_mode:
        template_to_use = TEMPLATE_TWO_SIDES_MG
        rig1_abs = os.path.abspath(TWO_SIDES_RIG1)
        rig2_abs = os.path.abspath(TWO_SIDES_RIG2)
        input_images_abs_dir = f"{rig1_abs} + {rig2_abs}"  # display only
    elif rig_mode:
        template_to_use = TEMPLATE_TURNTABLE_MG
        input_images_abs_dir = os.path.abspath(RIG_IMAGES)
    else:
        template_to_use = TEMPLATE_MG
        input_images_abs_dir = os.path.abspath(INPUT_IMAGES)

    print(f"\n{'='*55}")
    print(f"  MESHROOM PIPELINE - INITIALIZATION")
    print(f"{'='*55}")
    if two_sides_mode:
        print(f"  Mode:         TWO-SIDES (dual CameraInit)")
        print(f"  Template:     {template_to_use}")
        print(f"  Rig 1 (up):   {rig1_abs}")
        print(f"  Rig 2 (flip): {rig2_abs}")
    else:
        print(f"  Mode:         {'RIG (multi-camera)' if rig_mode else 'SINGLE (flat)'}")
        print(f"  Input images: {input_images_abs_dir}")
    print(f"  Output dir:   {output_dir_abs}")

    # -- Step 1: Prepare template ----------------------------------------
    print(f"\n[1/4] Preparing pipeline template...")
    prepare_pipeline(template_to_use, temp_mg_path)


    # Download Images from R2
    if not MESHROOM_EXE.startswith("D:"):
        progress_update(job, {
            "status": "Downloading images...",
            "progress": 20
        })
        r2.download_every_img_from_bucket(
            local_dir       = RIG_IMAGES if rig_mode else INPUT_IMAGES,
            bucket          = R2_PIPELINE_IMAGES_BUCKET,
            rig_mode        = rig_mode,
            two_sides_mode  = two_sides_mode,
        )

    # -- Step 1b (two-sides only): Run aliceVision_cameraInit for each rig
    #    and inject the generated .sfm paths into the template JSON ----------
    if two_sides_mode:
        print(f"\n[1b/4] Initializing cameras for two-sides mode...")

        # Locate aliceVision_cameraInit next to meshroom_batch
        meshroom_dir = os.path.dirname(os.path.abspath(MESHROOM_EXE))
        camera_init_exe = os.path.join(meshroom_dir, "aliceVision", "bin", "aliceVision_cameraInit")
        if os.name == "nt":
            camera_init_exe += ".exe"

        # Sensor database used by CameraInit for lens profile matching
        sensor_db = os.path.join(meshroom_dir, "aliceVision", "share", "aliceVision", "cameraSensors.db")

        sfm_paths = {}  # {"CameraInit_1": "/abs/path/cameraInit_rig1.sfm", ...}
        for ci_node, rig_dir in [("CameraInit_1", rig1_abs), ("CameraInit_2", rig2_abs)]:
            sfm_output = os.path.join(output_dir_abs, f"cameraInit_{ci_node}.sfm")
            ci_cmd = [
                camera_init_exe,
                "--imageFolder", rig_dir,
                "--output", sfm_output,
                "--verboseLevel", "warning",
            ]
            if os.path.exists(sensor_db):
                ci_cmd += ["--sensorDatabase", sensor_db]

            print(f"  Running CameraInit for {ci_node}: {rig_dir}")
            ci_result = subprocess.run(ci_cmd, capture_output=True, text=True)
            if ci_result.returncode != 0:
                print(f"  [ERROR] CameraInit failed for {ci_node}: {ci_result.stderr}")
                raise RuntimeError(f"aliceVision_cameraInit failed for {ci_node}")

            if not os.path.exists(sfm_output):
                raise RuntimeError(f"CameraInit did not produce output: {sfm_output}")

            sfm_paths[ci_node] = sfm_output
            print(f"  {ci_node} -> {sfm_output}")

        # Inject the .sfm file paths into the template JSON.
        # Replace each CameraInit node's empty viewpoints with a reference
        # to the generated .sfm file via the --input mechanism.
        # We modify the JSON so that the nodes following CameraInit read
        # from the .sfm output directly.
        with open(temp_mg_path, "r", encoding="utf-8") as f:
            pipeline_data = json.load(f)

        graph = pipeline_data.get("graph", {})
        for ci_node, sfm_path in sfm_paths.items():
            # Load the .sfm file and extract viewpoints + intrinsics
            with open(sfm_path, "r", encoding="utf-8") as f:
                sfm_data = json.load(f)

            viewpoints = sfm_data.get("views", [])
            intrinsics = sfm_data.get("intrinsics", [])

            # Convert SfM views to CameraInit viewpoints format
            ci_viewpoints = []
            for view in viewpoints:
                ci_viewpoints.append({
                    "viewId": view.get("viewId", -1),
                    "poseId": view.get("poseId", -1),
                    "path": view.get("path", ""),
                    "intrinsicId": view.get("intrinsicId", -1),
                    "rigId": view.get("rigId", -1),
                    "subPoseId": view.get("subPoseId", -1),
                    "metadata": view.get("metadata", ""),
                })

            # Convert SfM intrinsics to CameraInit intrinsics format
            ci_intrinsics = []
            for intr in intrinsics:
                ci_intrinsics.append({
                    "intrinsicId": intr.get("intrinsicId", -1),
                    "initialFocalLength": intr.get("focalLength", -1),
                    "focalLength": intr.get("focalLength", -1),
                    "pixelRatio": intr.get("pixelRatio", 1.0),
                    "pixelRatioLocked": intr.get("pixelRatioLocked", True),
                    "type": intr.get("type", "radial3"),
                    "width": intr.get("width", 0),
                    "height": intr.get("height", 0),
                    "sensorWidth": intr.get("sensorWidth", -1),
                    "sensorHeight": intr.get("sensorHeight", -1),
                    "serialNumber": intr.get("serialNumber", ""),
                    "principalPoint": intr.get("principalPoint", {"x": 0, "y": 0}),
                    "distortionParams": intr.get("distortionParams", []),
                    "locked": intr.get("locked", False),
                })

            if ci_node in graph:
                graph[ci_node]["inputs"]["viewpoints"] = ci_viewpoints
                graph[ci_node]["inputs"]["intrinsics"] = ci_intrinsics
                print(f"  Injected {len(ci_viewpoints)} viewpoints + "
                      f"{len(ci_intrinsics)} intrinsics into {ci_node}")

        with open(temp_mg_path, "w", encoding="utf-8") as f:
            json.dump(pipeline_data, f, indent=4)


    # -- Step 2: Run Meshroom --------------------------------------------
    print(f"\n[2/4] Running Meshroom (this may take several minutes)...")

    progress_update(job, {
        "status": "Running Meshroom (this may take several minutes)...",
        "progress": 40
    })
    
    if two_sides_mode:
        # Viewpoints already injected — run without --input
        command = [
            MESHROOM_EXE,
            "--pipeline", temp_mg_path,
            "--cache",    cache_dir,
            "--verbose",  "info",
        ]
    else:
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

    progress_update(job, {
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
    progress_update(job, {
        "status": "Post-processing...",
        "progress": 80
    })

    gc.collect()

    # High -> STL, 3MF & GLB
    if obj_high:
        high_stl_path = os.path.join(output_dir_abs, "high_model.stl")
        high_3mf_path = os.path.join(output_dir_abs, "high_model.3mf")
        convert_obj_to_print_formats(obj_high, high_stl_path, high_3mf_path)
        gc.collect()
        
        # High -> GLB for viewing with compressed JPGs
        high_glb_path = os.path.join(output_dir_abs, "high_model.glb")
        convert_obj_to_glb(dest_high, high_glb_path, compress_textures=True, draco=True)
        gc.collect()

    # Low -> STL, 3MF & GLB
    if obj_low:
        low_stl_path = os.path.join(output_dir_abs, "low_model.stl")
        low_3mf_path = os.path.join(output_dir_abs, "low_model.3mf")
        convert_obj_to_print_formats(obj_low, low_stl_path, low_3mf_path)
        gc.collect()

        glb_path = os.path.join(output_dir_abs, "low_model.glb")
        convert_obj_to_glb(dest_low, glb_path, compress_textures=True, draco=True)
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
    for fname in ["high_model.stl", "low_model.stl", "high_model.3mf", "low_model.3mf", "high_model.glb", "low_model.glb"]:
        fpath = os.path.join(output_dir_abs, fname)
        if os.path.exists(fpath):
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            print(f"\n  {fname} ({size_mb:.1f} MB)")

    print(f"\n  All files in: {output_dir_abs}")
    print(f"{'='*55}\n")

    if not MESHROOM_EXE.startswith("D:"):
        progress_update(job, {
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
