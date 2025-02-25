from time import time_ns

from flask import current_app
from google.cloud import storage

from src import config


class GoogleCloudStorage:
    client: storage.Client
    bucket: storage.Bucket

    def __init__(self, bucket_name=config.cfg.google_cloud_services.storage_bucket):
        self.client = storage.Client()
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
            current_app.logger.error(
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

    def get_file_link(self, filename: str):
        blob = self.bucket.get_blob(blob_name=filename)
        if blob is None:
            current_app.logger.error(
                f"Cannot find {filename} in the bucket:{self.bucket.name} on GoogleCloudStorage",
            )

            return None

        return blob.public_url
