import re
from time import time_ns

from flask import current_app
from google.cloud.storage import Bucket, Client

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
        file_names = [re.sub(f"{self.client.api_endpoint}/{self.bucket.name}/", "", file_url) for file_url in file_urls]
        self.bucket.delete_blobs(file_names)

    def get_file_link(self, filename: str):
        blob = self.bucket.get_blob(blob_name=filename)
        if blob is None:
            current_app.logger.error(
                f"Cannot find {filename} in the bucket:{self.bucket.name} on GoogleCloudStorage",
            )

            return None

        return blob.public_url
