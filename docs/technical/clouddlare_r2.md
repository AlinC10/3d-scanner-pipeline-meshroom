# `clouddlare_r2.py`

## API Reference

- **`R2_PIPELINE_IMAGES_BUCKET`** = `'photogrammetry-pipeline'`
- **`INPUT_IMAGES`** = `'./input_images'`
- **`RIG_IMAGES`** = `'./input_images/rig'`
- **`TWO_SIDES_RIG1`** = `'./input_images/rig1'`
- **`TWO_SIDES_RIG2`** = `'./input_images/rig2'`
- **`OUTPUT_DIR`** = `'./output'`
### `def delete_file(object_name, bucket=R2_PIPELINE_IMAGES_BUCKET)`
> Delete a file from an S3 bucket.
> :param object_name: S3 object name
> :type object_name: str
> :param bucket: Bucket to delete from
> :type bucket: str
> :return: True if file was deleted, else False
> :rtype: bool

### `def delete_all_files_from_bucket(bucket=R2_PIPELINE_IMAGES_BUCKET)`
> Delete all files from R2 bucket.
> :param bucket: Bucket to delete from
> :type bucket: str
> :return: None
> :rtype: None

### `def upload_file(file_name, bucket=R2_PIPELINE_IMAGES_BUCKET, object_name=None)`
> Upload a file to an S3 bucket
> :param file_name: File to upload
> :type file_name: str
> :param bucket: Bucket to upload to
> :type bucket: str
> :param object_name: S3 object name. If not specified then file_name is used
> :type object_name: str | None
> :return: True if file was uploaded, else False
> :rtype: bool

### `def create_output_zip(folder_path, zip_path)`
> Builds a structured ZIP from the pipeline output directory.
> 
> ZIP layout:
>     obj/high/       <- all files from Texturing_1/
>     obj/low/        <- all files from Texturing_2/
>     glb/high_model.glb
>     glb/low_model.glb
>     stl/high_model.stl
>     stl/low_model.stl
>     3mf/high_model.3mf
>     3mf/low_model.3mf
> :param folder_path: Absolute or relative path to the output directory.
> :type folder_path: str
> :param zip_path: Destination path for the .zip file.
> :type zip_path: str
> :return: zip_path on success, raises on error.
> :rtype: str

### `def upload_generated_obj(folder_path, object_name='output.zip', bucket=R2_PIPELINE_IMAGES_BUCKET)`
> Zips the pipeline output directory and uploads it to R2.
> 
> ZIP structure:
>     obj/high/       <- Texturing_1 contents (OBJ + PNG textures)
>     obj/low/        <- Texturing_2 contents (OBJ + JPG textures)
>     glb/high_model.glb
>     glb/low_model.glb
>     stl/high_model.stl
>     stl/low_model.stl
>     3mf/high_model.3mf
>     3mf/low_model.3mf
> :param folder_path: Relative or absolute path to the output directory.
> :type folder_path: str
> :param object_name: Key used when storing the file in R2.
> :type object_name: str
> :param bucket: Bucket to download from
> :type bucket: str
> :return: True if upload succeeded, False otherwise.
> :rtype: bool

### `def download_file(object_name, file_name=None, bucket=R2_PIPELINE_IMAGES_BUCKET)`
> Download a file from an S3 bucket
> :param object_name: S3 object name
> :type object_name: str
> :param file_name: File to download. If not specified then object_name is used
> :type file_name: str | None
> :param bucket: Bucket to download from
> :type bucket: str
> :return: True if file was downloaded, else False
> :rtype: bool

### `def download_every_img_from_bucket(local_dir=INPUT_IMAGES, bucket=R2_PIPELINE_IMAGES_BUCKET, rig_mode=False, two_sides_mode=False)`
> Download all images from the R2 bucket to a local directory.
> 
> Single mode (rig_mode=False, two_sides_mode=False):
>     Downloads all objects flat into `local_dir/`.
>     R2 keys: IMG_0001.jpg  →  local_dir/IMG_0001.jpg
> 
> Rig mode (rig_mode=True):
>     Downloads all objects preserving subfolder structure into RIG_IMAGES.
>     R2 keys: rig/0/0001.jpg  →  input_images/rig/0/0001.jpg
>              rig/1/0001.jpg  →  input_images/rig/1/0001.jpg
> 
> Two-sides mode (two_sides_mode=True):
>     Downloads objects preserving rig1/rig2 subfolder structure.
>     R2 keys: rig1/0/0001.jpg  →  input_images/rig1/0/0001.jpg
>              rig1/1/0001.jpg  →  input_images/rig1/1/0001.jpg
>              rig2/0/0001.jpg  →  input_images/rig2/0/0001.jpg
>              rig2/1/0001.jpg  →  input_images/rig2/1/0001.jpg
> :param local_dir: Local directory to download images into (used in single mode).
> :type local_dir: str
> :param bucket: R2 bucket name.
> :type bucket: str
> :param rig_mode: If True, download rig-structured images.
> :type rig_mode: bool
> :param two_sides_mode: If True, download two-sides structured images into rig1/rig2.
> :type two_sides_mode: bool
> :return: None
> :rtype: None

### `def download_generated_obj(object_name='output.zip', dest_dir=None, bucket=R2_PIPELINE_IMAGES_BUCKET)`
> Downloads the output ZIP from R2 and extracts it into dest_dir.
> 
> Resulting layout after extraction:
>     dest_dir/obj/high/       <- OBJ + PNG textures
>     dest_dir/obj/low/        <- OBJ + JPG textures
>     dest_dir/glb/high_model.glb
>     dest_dir/glb/low_model.glb
>     dest_dir/stl/high_model.stl
>     dest_dir/stl/low_model.stl
>     dest_dir/3mf/high_model.3mf
>     dest_dir/3mf/low_model.3mf
> :param object_name: R2 key of the zip file (e.g. "output.zip").
> :type object_name: str
> :param dest_dir: Local directory where the zip is extracted. Created automatically if it does not exist.
> :type dest_dir: str | None
> :param bucket: Bucket to download from
> :type bucket: str
> :return: True if download + extraction succeeded, False otherwise.
> :rtype: bool
