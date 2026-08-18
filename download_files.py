import logging
import zipfile
from botocore.exceptions import ClientError
import os
from config import INPUT_IMAGES, s3, R2_PIPELINE_IMAGES_BUCKET

# bucket parameter is used for the name of the directory in the R2


def download_file(object_name: str, file_name: str = None, bucket: str = R2_PIPELINE_IMAGES_BUCKET) -> bool:
    """Download a file from an S3 bucket

    :param object_name: S3 object name
    :param file_name: File to download. If not specified then object_name is used
    :param bucket: Bucket to download from
    :return: True if file was downloaded, else False
    """

    # If file_name was not specified, use object_name
    if file_name is None:
        file_name = object_name

    # Download the file
    try:
        # s3.download_file('amzn-s3-demo-bucket', 'OBJECT_NAME', 'FILE_NAME')
        s3.download_file(bucket, object_name, file_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def download_every_img_from_bucket(local_dir: str = INPUT_IMAGES, bucket: str = R2_PIPELINE_IMAGES_BUCKET):
    response = s3.list_objects_v2(Bucket=bucket)
    os.makedirs(local_dir, exist_ok=True)

    print("Downloading images from R2...")
    if 'Contents' in response:
        for obj in response['Contents']:
            file_key = obj['Key']

            print(f"Downloading {file_key}...")
            
            download_file(file_key, os.path.join(local_dir,  os.path.basename(file_key)), bucket)
    print("Downloaded every image")


def download_generated_obj(object_name: str = "output.zip", dest_dir: str=None, bucket: str = R2_PIPELINE_IMAGES_BUCKET) -> bool:
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
    if not download_file(object_name, zip_path, bucket):
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
    finally:
        os.remove(zip_path)

    print(f"  [R2] Extraction complete: {dest_dir}")
    return True