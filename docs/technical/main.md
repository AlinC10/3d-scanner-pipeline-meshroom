# `main.py`

## API Reference

### `def progress_update(job, status_dict)`
> Updates the progress of the job.
> :param job: The job object.
> :type job: dict
> :param status_dict: The status dictionary.
> :type status_dict: dict
> :return: None
> :rtype: None

### `def _monitor_memory()`
> Monitors RAM and swap memory usage in a separate thread.
> :return: None
> :rtype: None

### `def prepare_pipeline(template_path, temp_mg_path)`
> Reads the .mg JSON template and saves it as a temporary file.
> 
> NOTE (Meshroom 2025): The Texturing node's 'output' field cannot be
> overridden via inputs (causes DescriptionConflict). Results are written
> to MeshroomCache and copied by this script afterward.
> 
> :param template_path: Path to the input .mg template file.
> :type template_path: str
> :param temp_mg_path: Path where the temporary .mg file will be saved.
> :type temp_mg_path: str
> :return: List of Texturing node names found in the template.
> :rtype: list

### `def find_texturing_cache_folders(cache_root)`
> Scans MeshroomCache/Texturing/ for folders containing texturedMesh.obj.
> 
> Returns dict: { 'high': <path with PNG textures>, 'low': <path with JPG textures> }
> Branches are identified by their texture file extensions:
>   - PNG textures -> High branch (full quality for printing)
>   - JPG textures -> Low branch (compressed for web)
>   
> :param cache_root: Path to the MeshroomCache root directory.
> :type cache_root: str
> :return: Dictionary containing paths to the high and low texturing cache folders.
> :rtype: dict

### `def copy_texturing_output(cache_folder, dest_folder, label)`
> Copies all relevant files (OBJ, MTL, textures) from a Texturing
> cache folder into the destination folder.
> 
> Returns the path to the copied texturedMesh.obj, or None on failure.
> 
> :param cache_folder: Path to the source cache folder.
> :type cache_folder: str
> :param dest_folder: Path to the destination folder.
> :type dest_folder: str
> :param label: Label for logging purposes.
> :type label: str
> :return: Path to the copied texturedMesh.obj, or None on failure.
> :rtype: str or None

### `def convert_obj_to_print_formats(obj_path, stl_path, mf_path)`
> Converts a high-poly OBJ mesh to watertight STL and 3MF formats for 3D printing.
> 
> :param obj_path: Path to the input OBJ file.
> :type obj_path: str
> :param stl_path: Path where the output STL file will be saved.
> :type stl_path: str
> :param mf_path: Path where the output 3MF file will be saved.
> :type mf_path: str
> :return: None
> :rtype: None

### `def _apply_draco_compression(glb_path, draco_glb_path, compression_level=7, quantization_bits=14)`
> Reads a GLB produced by trimesh and re-encodes all mesh primitive
> geometry buffers using Draco compression (KHR_draco_mesh_compression).
> 
> :param glb_path: Path to the input GLB file.
> :type glb_path: str
> :param draco_glb_path: Path where the output Draco compressed GLB will be saved.
> :type draco_glb_path: str
> :param compression_level: Draco compression level (0-10).
> :type compression_level: int
> :param quantization_bits: Number of bits for Draco quantization.
> :type quantization_bits: int
> :return: True if compression was successful, False otherwise.
> :rtype: bool

### `def convert_obj_to_glb(obj_folder, glb_path, compress_textures=True, draco=True, draco_level=7, draco_bits=14)`
> Packs an OBJ + MTL + texture images into a single GLB (binary glTF).
> 
> Stage 1 (trimesh): loads the OBJ, optionally re-encodes textures as JPG.
> Stage 2 (Draco, optional): re-encodes mesh geometry buffers with Draco.
> 
> :param obj_folder: Path to the folder containing the OBJ, MTL, and textures.
> :type obj_folder: str
> :param glb_path: Path where the output GLB file will be saved.
> :type glb_path: str
> :param compress_textures: Whether to compress textures to JPG.
> :type compress_textures: bool
> :param draco: Whether to apply Draco compression.
> :type draco: bool
> :param draco_level: Draco compression level.
> :type draco_level: int
> :param draco_bits: Number of bits for Draco quantization.
> :type draco_bits: int
> :return: None
> :rtype: None

### `def run_pipeline(job)`
> Orchestrates the full Meshroom photogrammetry pipeline:
> 
>   1. Prepares the pipeline template
>   2. Runs meshroom_batch with TMPDIR redirect (keeps cache local)
>   3. Copies results from cache into organized folders:
>         output/Texturing_1/  <- High (OBJ + PNG textures)
>         output/Texturing_2/  <- Low  (OBJ + JPG textures)
>   4. Post-processing:
>         - High branch -> STL for 3D printing
>         - Low branch  -> GLB for web (single binary, embedded textures)
>         
> :param job: Dictionary containing job configuration and inputs.
> :type job: dict
> :return: Dictionary containing the status of the pipeline run.
> :rtype: dict
