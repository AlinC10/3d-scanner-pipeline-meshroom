import logging
import zipfile
import boto3
from botocore.exceptions import ClientError
import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# bucket parameter is used for the name of the directory in the R2

load_dotenv()

s3 = boto3.client(
    service_name="s3",
    endpoint_url=os.environ.get("R2_ENDPOINT_URL"),
    aws_access_key_id=os.environ.get("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY"),
)

def upload_file(file_name: str, bucket: str = None, object_name: str = None) -> bool:
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    if bucket is None:
        bucket = os.environ.get("R2_BUCKET_NAME")

    # Upload the file
    try:
        s3.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def download_file(object_name: str, file_name: str = None, bucket: str = None) -> bool:
    """Download a file from an S3 bucket

    :param object_name: S3 object name
    :param file_name: File to download. If not specified then object_name is used
    :param bucket: Bucket to download from
    :return: True if file was downloaded, else False
    """

    # If file_name was not specified, use object_name
    if file_name is None:
        file_name = object_name

    if bucket is None:
        bucket = os.environ.get("R2_BUCKET_NAME")

    # Download the file
    try:
        # s3.download_file('amzn-s3-demo-bucket', 'OBJECT_NAME', 'FILE_NAME')
        s3.download_file(bucket, object_name, file_name)
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


def upload_generated_obj(folder_path: str, object_name: str = "output.zip") -> bool:
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

    success = upload_file(zip_path, object_name=object_name)
    if success:
        print(f"  [R2] Upload complete: {object_name}")
    else:
        print(f"  [R2] Upload FAILED for: {object_name}")

    return success


def download_generated_obj(object_name: str = "output.zip", dest_dir: str=None) -> bool:
    """
    Downloads the output ZIP from R2 and extracts it into dest_dir.

    Resulting layout after extraction:
        dest_dir/high_texture/   <- OBJ + PNG textures
        dest_dir/low_texture/    <- web_model.glb
        dest_dir/printable_model.stl

    :param object_name: R2 key of the zip file (e.g. "output.zip").
    :param dest_dir:    Local directory where the zip is extracted.
                        Created automatically if it does not exist.
    :return: True if download + extraction succeeded, False otherwise.
    """
    if not dest_dir:
        dest_dir = os.getcwd()

    os.makedirs(dest_dir, exist_ok=True)

    zip_path = os.path.join(dest_dir, "output.zip")

    print(f"  [R2] Downloading '{object_name}' -> {zip_path}")
    if not download_file(object_name, file_name=zip_path):
        print(f"  [R2] Download FAILED for: {object_name}")
        return False

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"  [R2] Downloaded ({size_mb:.1f} MB). Extracting to {dest_dir}...")

    try:
        with zipfile.ZipFile(zip_path, "r") as zipf:
            zipf.extractall(dest_dir)
    except zipfile.BadZipFile as e:
        logging.error("[R2] Extraction failed — bad zip: %s", e)
        return False

    print(f"  [R2] Extraction complete: {dest_dir}")
    return True