import subprocess
import os
import clouddlare_r2 as r2
from clouddlare_r2 import INPUT_IMAGES, RIG_IMAGES

def send_images(input_images_path: str = INPUT_IMAGES):
    """Upload flat single-camera images to R2.

    R2 keys will be the bare filenames: IMG_0001.jpg
    Use for mode='single'.
    """
    print(f"Uploading images to R2 (single mode)...")
    for img in os.listdir(input_images_path):
        img_path = os.path.join(input_images_path, img)
        if not os.path.isfile(img_path):
            continue
        print(f"  Uploading {img} to R2...")
        r2.upload_file(img_path)

    print("All images uploaded to R2")


def send_rig_images(rig_images_path: str = RIG_IMAGES):
    """Upload rig-structured images to R2 preserving the subfolder layout.

    Walks rig/0/ and rig/1/ (or any numeric subfolders) and uploads each
    image with an R2 key that mirrors the local structure:
        rig_images_path/0/0001.jpg  →  R2 key: rig/0/0001.jpg
        rig_images_path/1/0001.jpg  →  R2 key: rig/1/0001.jpg

    The download function in clouddlare_r2.py uses the same 'rig/' prefix
    to recreate this structure on the server.
    Use for mode='rig'.
    """
    print(f"Uploading rig images to R2 (rig mode)...")
    for cam_folder in sorted(os.listdir(rig_images_path)):
        cam_path = os.path.join(rig_images_path, cam_folder)
        if not os.path.isdir(cam_path):
            continue
        for img in sorted(os.listdir(cam_path)):
            img_path = os.path.join(cam_path, img)
            if not os.path.isfile(img_path):
                continue
            # R2 key mirrors the rig structure: rig/<cam_folder>/<filename>
            r2_key = f"rig/{cam_folder}/{img}"
            print(f"  Uploading {r2_key}...")
            r2.upload_file(img_path, object_name=r2_key)

    print("All rig images uploaded to R2")


def download_result():
    print("Download resulted model")
    r2.download_generated_obj("output.zip", "./output")
    print("Model downloaded!")

def delete_all_files():
    print("Cleaning up R2 bucket...")
    r2.delete_all_files_from_bucket()
    print("R2 bucket cleaned up!")


if __name__ == "__main__":
    print("Starting the simulation...")

    # send_images()
    # send_rig_images()
    
    # Run a Docker command
    print("Run Docker Container...")
    result = subprocess.run(
        args="docker run --gpus all --env-file .env -i -v \"D:/Docker_Meshroom:/runpod-volume\" meshroom_pipeline",
        text=True,
        check=True,
        shell=True
    )

    print("Docker Container Finishes its job!")

    download_result()
    delete_all_files()

