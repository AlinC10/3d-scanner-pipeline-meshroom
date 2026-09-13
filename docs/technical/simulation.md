# `simulation.py`

## API Reference

### `def send_images(input_images_path=INPUT_IMAGES)`
> Upload flat single-camera images to R2.
> 
> R2 keys will be the bare filenames: IMG_0001.jpg
> Use for mode='single'.

### `def send_rig_images(rig_images_path=RIG_IMAGES)`
> Upload rig-structured images to R2 preserving the subfolder layout.
> 
> Walks 0/ and 1/ (or any numeric subfolders) and uploads each
> image with an R2 key that mirrors the local structure:
>     rig_images_path/0/0001.jpg  →  R2 key: rig/0/0001.jpg
>     rig_images_path/1/0001.jpg  →  R2 key: rig/1/0001.jpg
> 
> Use for mode='rig'.

### `def send_two_sides_images(rig1_path=TWO_SIDES_RIG1, rig2_path=TWO_SIDES_RIG2)`
> Upload two-sides rig-structured images to R2.
> 
> Walks rig1/ and rig2/ (each containing 0/ and 1/ camera subfolders)
> and uploads each image with an R2 key that mirrors the local structure:
>     rig1_path/0/0001.jpg  →  R2 key: rig1/0/0001.jpg
>     rig1_path/1/0001.jpg  →  R2 key: rig1/1/0001.jpg
>     rig2_path/0/0001.jpg  →  R2 key: rig2/0/0001.jpg
>     rig2_path/1/0001.jpg  →  R2 key: rig2/1/0001.jpg
> 
> Use for mode='two-sides'.

### `def download_result()`
*No docstring available.*

### `def delete_all_files()`
*No docstring available.*
