import logging
from botocore.exceptions import ClientError
from config import s3, R2_PIPELINE_IMAGES_BUCKET


def delete_file(object_name: str, bucket: str = R2_PIPELINE_IMAGES_BUCKET) -> bool:
    """Delete a file from an S3 bucket

    :param object_name: S3 object name
    :param bucket: Bucket to delete from
    :return: True if file was deleted, else False
    """
    # Delete the file
    try:
        s3.delete_object(Bucket=bucket, Key=object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def delete_all_files_from_bucket(bucket: str = R2_PIPELINE_IMAGES_BUCKET) -> None:
    """Delete all files from R2 bucket.

    :param bucket: Bucket to delete from
    """        
    response = s3.list_objects_v2(Bucket=bucket)

    if 'Contents' in response:
        # 2. Build a list of files to delete
        objects_to_delete = [
            {'Key': obj['Key']} 
            for obj in response['Contents'] 
        ]
        
        # 3. Delete them all in one batch operation (Free operation!)
        if objects_to_delete:
            s3.delete_objects(
                Bucket=bucket,
                Delete={'Objects': objects_to_delete}
            )
            print(f"Cleaned up {len(objects_to_delete)} old files. Bucket is ready for the next scan!")

        return
    
    print("No files found in the bucket.")