import re
from datetime import UTC, datetime
from functools import lru_cache
from time import time_ns

from flask import current_app
from google.cloud.storage import Client
from werkzeug.datastructures import FileStorage

# GOOGLE CLOUD STORAGE doesn't accept extreme datetime values like 3000 AD as custom time
# For whoever sees this code in 2100 AD, please update the value!!!
GCS_MAX_DATETIME_LIMIT = datetime(2100, 10, 31, tzinfo=UTC)


@lru_cache
def get_gcs_client():
    return Client()


class GoogleCloudStorage:
    client: Client

    def __init__(self):
        self.client = get_gcs_client()

    def _get_bucket(self, bucket_name: str):
        return self.client.bucket(bucket_name)

    def upload_content(
        self,
        filename: str,
        content: FileStorage,
        *,
        bucket_name: str,
        make_file_public: bool = False,
    ):
        start_ns = time_ns()

        bucket = self._get_bucket(bucket_name)

        blob = bucket.blob(filename)
        blob.upload_from_file(file_obj=content.stream, content_type=content.content_type, rewind=True)
        if make_file_public:
            blob.make_public()

        end_ns = time_ns()

        current_app.logger.info({
            "service": "GoogleCloudStorage",
            "action": "upload",
            "filename": filename,
            "duration_ms": (end_ns - start_ns) / 1_000_000,
        })

        return blob.public_url

    def delete_file(self, filename: str, bucket_name: str, *, raise_exception_on_failure=False):
        start_ns = time_ns()
        bucket = self._get_bucket(bucket_name)

        try:
            bucket.delete_blob(blob_name=filename)
        except Exception:
            current_app.logger.exception(
                "Failed to delete %s from the bucket:%s on GoogleCloudStorage", filename, bucket.name
            )

            if raise_exception_on_failure:
                raise

        end_ns = time_ns()

        current_app.logger.info({
            "service": "GoogleCloudStorage",
            "action": "delete",
            "filename": filename,
            "duration_ms": (end_ns - start_ns) / 1_000_000,
        })

    def delete_multiple_files_by_url(self, file_urls: list[str], bucket_name: str):
        start_ns = time_ns()

        bucket = self._get_bucket(bucket_name)

        file_names = [re.sub(f"{self.client.api_endpoint}/{bucket.name}/", "", file_url) for file_url in file_urls]

        found_blobs = []
        for name in file_names:
            blob = bucket.get_blob(blob_name=name)
            if blob is not None:
                found_blobs.append(blob)

        blob_names = [blob.name for blob in found_blobs]

        try:
            bucket.delete_blobs(found_blobs)
        except Exception as e:
            current_app.logger.exception(
                f"Failed to delete {','.join(blob_names)} from the bucket:{bucket.name} on GoogleCloudStorage",
                repr(e),
            )

        end_ns = time_ns()

        current_app.logger.info({
            "service": "GoogleCloudStorage",
            "action": "batch_delete",
            "filename": ",".join(blob_names),
            "duration_ms": (end_ns - start_ns) / 1_000_000,
        })

    def update_file_deletion_time(self, filename: str, new_time: datetime, bucket_name):
        if new_time > GCS_MAX_DATETIME_LIMIT:
            current_app.logger.info(f"The new datetime for {filename} is over GoogleCloudStorage limit")
            raise Exception

        bucket = self._get_bucket(bucket_name)

        start_ns = time_ns()
        try:
            blob = bucket.get_blob(blob_name=filename)
            if blob is None:
                current_app.logger.error(
                    f"Cannot find {filename} in the bucket:{bucket.name} on GoogleCloudStorage",
                )

                raise Exception

            blob.custom_time = new_time
            blob.patch()

        except Exception:
            current_app.logger.exception(
                f"Failed to update the metadata of {filename} in the bucket:{bucket.name} on GoogleCloudStorage",
            )

            return None

        end_ns = time_ns()

        current_app.logger.info({
            "service": "GoogleCloudStorage",
            "action": "update_file_deletion_time",
            "filename": filename,
            "duration_ms": (end_ns - start_ns) / 1_000_000,
        })

    def migrate_anonymous_file(self, filename: str, bucket_name: str):
        current_app.logger.info(
            f"Migrating {filename} from anonymous to normal in the bucket:{bucket_name} on GoogleCloudStorage",
        )
        # GCS doesn't allow unsetting custom time, instead we're setting it to the furthest time possible
        self.update_file_deletion_time(filename, GCS_MAX_DATETIME_LIMIT, bucket_name=bucket_name)
