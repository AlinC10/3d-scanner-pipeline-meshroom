import boto3
import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

INPUT_IMAGES="./input_images"

MESHROOM_EXE="../runpod-volume/Meshroom-2025.1.0/meshroom_batch"
# MESHROOM_EXE="D:/Meshroom-2025.1.0/meshroom_batch.exe"

OUTPUT_DIR="./output"

TEMPLATE_MG="./template.mg"

# Cloudflare R2 connection

s3 = boto3.client(
    service_name="s3",
    endpoint_url=os.environ.get("R2_ENDPOINT_URL"),
    aws_access_key_id=os.environ.get("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY"),
)

# R2 bucket that will only be used for hosting images that will be used in the Meshroom pipeline
# and after that will be deleted
R2_PIPELINE_IMAGES_BUCKET="photogrammetry-pipeline"