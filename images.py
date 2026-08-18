import os

INPUT_IMAGES="./dataset_test/input_images"

def get_file_path() -> str:
    """Returns the absolute path to the input images folder."""
    
    if not os.path.exists(INPUT_IMAGES):
        print(f"[ERROR] Input images folder not found: {INPUT_IMAGES}")
        os.makedirs(INPUT_IMAGES, exist_ok=True)
    
    return os.path.abspath(INPUT_IMAGES)

