import subprocess
import os
import clouddlare_r2 as r2
from clouddlare_r2 import INPUT_IMAGES

def send_images(input_images_path: str = INPUT_IMAGES):
    print(f"Uploading images to R2...")
    for img in os.listdir(input_images_path):
        # upload every image to R2
        print(f"  Uploading {img} to R2...")
        img_path = os.path.join(input_images_path, img)
        r2.upload_file(img_path)
        # os.remove(img_path)

    # os.rmdir(input_images_path)
    print("All images uploaded to R2")

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

