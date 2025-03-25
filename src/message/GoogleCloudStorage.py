import re
from time import time_ns

from flask import current_app
from google.cloud.storage import Bucket, Client
from google.cloud.storage.blob import Blob

from src.config import get_config


class GoogleCloudStorage:
    client: Client
    bucket: Bucket

    def __init__(self, bucket_name=get_config.cfg.google_cloud_services.storage_bucket):
        self.client = Client()
        self.bucket = self.client.bucket(bucket_name)

    def upload_content(self, filename: str, content: bytes | str, content_type: str = "text/plain"):
        start_ns = time_ns()
        blob = self.bucket.blob(filename)
        blob.upload_from_string(data=content, content_type=content_type)
        blob.make_public()
        end_ns = time_ns()

        current_app.logger.info({
            "service": "GoogleCloudStorage",
            "action": "upload",
            "filename": filename,
            "duration_ms": (end_ns - start_ns) / 1_000_000,
        })

        return blob.public_url

    def delete_file(self, filename: str):
        start_ns = time_ns()
        try:
            self.bucket.delete_blob(blob_name=filename)
        except Exception as e:
            current_app.logger.exception(
                f"Failed to delete {filename} from the bucket:{self.bucket.name} on GoogleCloudStorage",
                repr(e),
            )

        end_ns = time_ns()

        current_app.logger.info({
            "service": "GoogleCloudStorage",
            "action": "delete",
            "filename": filename,
            "duration_ms": (end_ns - start_ns) / 1_000_000,
        })

    def delete_multiple_files_by_url(self, file_urls: list[str]):
        start_ns = time_ns()
        
        file_names = [re.sub(f"{self.client.api_endpoint}/{self.bucket.name}/", "", file_url) for file_url in file_urls]
        
        found_blobs = []
        for name in file_names:
            blob = self.bucket.get_blob(blob_name=name)
            if (blob is not None):
                found_blobs.append(blob)
        
        blob_names = [blob.name for blob in found_blobs]

        try:
            self.bucket.delete_blobs(found_blobs)
        except Exception as e:
            current_app.logger.exception(
                f"Failed to delete {','.join(blob_names)} from the bucket:{self.bucket.name} on GoogleCloudStorage",
                repr(e),
            )

        end_ns = time_ns()

        current_app.logger.info({
            "service": "GoogleCloudStorage",
            "action": "batch_delete",
            "filename": ','.join(blob_names),
            "duration_ms": (end_ns - start_ns) / 1_000_000,
        })

    def move_file(self, old_name: str, new_name: str):
        start_ns = time_ns()
        try:
            source_blob = self.bucket.get_blob(blob_name=old_name)
            if source_blob is None:
                current_app.logger.error(
                    f"Cannot find {old_name} in the bucket:{self.bucket.name} on GoogleCloudStorage",
                )

                raise Exception

            new_blob = self.bucket.rename_blob(source_blob, new_name=new_name)
            new_blob.make_public()

        except Exception as e:
            current_app.logger.exception(
                f"Failed to move {old_name} to {new_name} in the bucket:{self.bucket.name} on GoogleCloudStorage",
                repr(e),
            )

            return None

        end_ns = time_ns()
        current_app.logger.info({
            "service": "GoogleCloudStorage",
            "action": "move",
            "filename": f"{old_name} ==> {new_name}",
            "duration_ms": (end_ns - start_ns) / 1_000_000,
        })

        return new_blob.public_url