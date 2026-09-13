# `pod_entrypoint.py`

## API Reference

- **`MESHROOM_URL`** = `'https://zenodo.org/records/16887472/files/Meshroom-2025.1.0-Linux.tar.gz'`
- **`MESHROOM_FALLBACK_URL`** = `os.getenv('MESHROOM_FALLBACK_URL', '')`
- **`DOWNLOAD_PATH`** = `'/workspace/Meshroom.tar.gz'`
- **`EXTRACT_PATH`** = `'/workspace'`
- **`MESHROOM_DIR`** = `os.path.join(EXTRACT_PATH, 'Meshroom-2025.1.0')`
- **`MESHROOM_EXE`** = `os.path.join(MESHROOM_DIR, 'meshroom_batch')`
### `def mem_total_gb()`
> Get the total system memory in gigabytes.
> :return: The total memory in GB.
> :rtype: int

### `def download_and_extract_meshroom()`
> Download and extract the Meshroom package.
> :return: None
> :rtype: None
