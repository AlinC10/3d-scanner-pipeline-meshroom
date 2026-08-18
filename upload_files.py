import logging
import zipfile
from botocore.exceptions import ClientError
import os
from config import s3, R2_PIPELINE_IMAGES_BUCKET

# bucket parameter is used for the name of the directory in the R2

def upload_file(file_name: str, bucket: str = R2_PIPELINE_IMAGES_BUCKET, object_name: str = None) -> bool:
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    try:
        s3.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def create_output_zip(folder_path: str, zip_path: str) -> str:
    """
    Builds a structured ZIP from the pipeline output directory.

    ZIP layout:
        high_texture/   <- all files from Texturing_1/
        low_texture/    <- web_model.glb
        printable_model.stl  (root)

    :param folder_path: Absolute or relative path to the output directory.
    :param zip_path:    Destination path for the .zip file.
    :return: zip_path on success, raises on error.
    """
    texturing1_dir = os.path.join(folder_path, "Texturing_1")
    glb_file       = os.path.join(folder_path, "web_model.glb")
    stl_file       = os.path.join(folder_path, "printable_model.stl")

    os.makedirs(os.path.dirname(os.path.abspath(zip_path)), exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # --- high_texture/ : everything inside Texturing_1/ ---
        if os.path.isdir(texturing1_dir):
            for fname in os.listdir(texturing1_dir):
                fpath = os.path.join(texturing1_dir, fname)
                if os.path.isfile(fpath):
                    zipf.write(fpath, os.path.join("high_texture", fname))
        else:
            logging.warning("[ZIP] Texturing_1 directory not found: %s", texturing1_dir)

        # --- low_texture/ : web_model.glb ---
        if os.path.isfile(glb_file):
            zipf.write(glb_file, os.path.join("low_texture", "web_model.glb"))
        else:
            logging.warning("[ZIP] GLB file not found: %s", glb_file)

        # --- root : printable_model.stl ---
        if os.path.isfile(stl_file):
            zipf.write(stl_file, "printable_model.stl")
        else:
            logging.warning("[ZIP] STL file not found: %s", stl_file)

    return zip_path


def upload_generated_obj(folder_path: str, object_name: str = "output.zip", bucket: str = R2_PIPELINE_IMAGES_BUCKET) -> bool:
    """
    Zips the pipeline output directory and uploads it to R2.

    ZIP structure:
        high_texture/   <- Texturing_1 contents (OBJ + PNG textures)
        low_texture/    <- web_model.glb
        printable_model.stl

    :param folder_path:  Relative or absolute path to the output directory.
    :param object_name:  Key used when storing the file in R2.
    :return: True if upload succeeded, False otherwise.
    """
    zip_path = os.path.join(folder_path, "output.zip")

    print(f"  [R2] Building zip archive -> {zip_path}")
    try:
        create_output_zip(folder_path, zip_path)
    except Exception as e:
        logging.error("[R2] Failed to create zip: %s", e)
        return False

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"  [R2] Zip ready ({size_mb:.1f} MB). Uploading as '{object_name}'...")

    success = upload_file(zip_path, bucket, object_name)
    if success:
        print(f"  [R2] Upload complete: {object_name}")
    else:
        print(f"  [R2] Upload FAILED for: {object_name}")

    return success