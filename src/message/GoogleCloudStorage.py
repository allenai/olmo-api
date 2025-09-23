import re
from datetime import UTC, datetime
from time import time_ns

from flask import current_app
from google.cloud.storage import Bucket, Client

from src.config.get_config import get_config

# GOOGLE CLOUD STORAGE doesn't accept extreme datetime values like 3000 AD as custom time
# For whoever sees this code in 2100 AD, please update the value!!!
GCS_MAX_DATETIME_LIMIT = datetime(2100, 10, 31, tzinfo=UTC)


class GoogleCloudStorage:
    client: Client
    bucket: Bucket

    def __init__(self, bucket_name: str | None = None):
        self.client = Client()
        if bucket_name is None:
            bucket_name = get_config().google_cloud_services.storage_bucket
        self.bucket = self.client.bucket(bucket_name)

    def upload_content(
        self, filename: str, content: bytes | str, content_type: str = "text/plain", is_anonymous: bool = False
    ):
        start_ns = time_ns()

        blob = self.bucket.blob(filename)
        blob.upload_from_string(data=content, content_type=content_type)
        blob.make_public()

        # We're using the file's custom time to have GCS automatically delete files associated with anonymous msgs
        if is_anonymous:
            blob.custom_time = datetime.now(UTC)
            blob.patch()

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
            if blob is not None:
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
            "filename": ",".join(blob_names),
            "duration_ms": (end_ns - start_ns) / 1_000_000,
        })

    def update_file_deletion_time(self, filename: str, new_time: datetime):
        if new_time > GCS_MAX_DATETIME_LIMIT:
            current_app.logger.info(f"The new datetime for {filename} is over GoogleCloudStorage limit")
            raise Exception

        start_ns = time_ns()
        try:
            blob = self.bucket.get_blob(blob_name=filename)
            if blob is None:
                current_app.logger.error(
                    f"Cannot find {filename} in the bucket:{self.bucket.name} on GoogleCloudStorage",
                )

                raise Exception

            blob.custom_time = new_time
            blob.patch()

        except Exception as e:
            current_app.logger.error(
                f"Failed to update the metadata of {filename} in the bucket:{self.bucket.name} on GoogleCloudStorage",
                repr(e),
            )

            return None

        end_ns = time_ns()

        current_app.logger.info({
            "service": "GoogleCloudStorage",
            "action": "update_file_deletion_time",
            "filename": filename,
            "duration_ms": (end_ns - start_ns) / 1_000_000,
        })

    def migrate_anonymous_file(self, filename: str):
        current_app.logger.info(
            f"Migrating {filename} from anonymous to normal in the bucket:{self.bucket.name} on GoogleCloudStorage",
        )
        # GCS doesn't allow unsetting custom time, instead we're setting it to the furthest time possible
        self.update_file_deletion_time(filename, GCS_MAX_DATETIME_LIMIT)
