import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from time import time_ns
from typing import BinaryIO

from gcloud.aio.storage import Storage
from opentelemetry import trace

from core.logger import CoreLogger

logger = CoreLogger("google_cloud")

# GOOGLE CLOUD STORAGE doesn't accept extreme datetime values like 3000 AD as custom time
# For whoever sees this code in 2100 AD, please update the value!!!
GCS_MAX_DATETIME_LIMIT = datetime(2100, 10, 31, tzinfo=UTC)

tracer = trace.get_tracer(__name__)


@dataclass(kw_only=True)
class UploadResponse:
    public_url: str
    storage_path: str


class GoogleCloudStorage:
    def __init__(self, session=None):
        """
        session: aiohttp.ClientSession
                    supply if you want to manage the session yourself
                    None (the default) uses default gcloud.aio.Storage session management

            ex:
                with aiohttp.ClientSession() as session:
                    cloud_storage = GoogleCloudStorage(session=session)
                    ...
        """
        self.session = session

    @tracer.start_as_current_span("GoogleCloudStorageService/upload_content")
    async def upload_content(
        self,
        filename: str,
        file_data: BinaryIO | bytes,
        *,
        bucket_name: str,
        content_type: str | None = None,
        make_file_public: bool = False,
        timeout: int = 60,  # default in sync GCS (google.aio.storage default is 30s)
    ) -> UploadResponse:
        start_ns = time_ns()

        async with Storage(session=self.session) as client:
            await client.upload(
                bucket=bucket_name,
                object_name=filename,
                file_data=file_data,
                content_type=content_type,
                parameters={"predefinedAcl": "publicRead"} if make_file_public else None,
                timeout=timeout,
            )

        end_ns = time_ns()

        logger.info(
            "GoogleCloudStorage Upload",
            bucket=bucket_name,
            filename=filename,
            duration_ms=(end_ns - start_ns) / 1_000_000,
        )

        # Construct URLs
        public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
        storage_path = f"gs://{bucket_name}/{filename}"

        return UploadResponse(public_url=public_url, storage_path=storage_path)

    async def delete_file(self, filename: str, bucket_name: str, *, raise_exception_on_failure=False) -> None:
        start_ns = time_ns()

        try:
            async with Storage(session=self.session) as client:
                # return value?
                await client.delete(bucket=bucket_name, object_name=filename)

        except Exception:
            logger.exception("GoogleCloudStorage Delete Error", bucket=bucket_name, filename=filename)
            if raise_exception_on_failure:
                raise

        end_ns = time_ns()

        logger.info(
            "GoogleCloudStorage Delete",
            bucket=bucket_name,
            filename=filename,
            duration_ms=(end_ns - start_ns) / 1_000_000,
        )

    async def delete_multiple_files_by_url(
        self, file_urls: list[str], bucket_name: str, *, raise_exception_on_failure=False
    ) -> None:
        start_ns = time_ns()

        base_url = f"https://storage.googleapis.com/{bucket_name}/"
        file_names = [re.sub(base_url, "", file_url) for file_url in file_urls]

        try:
            async with Storage(session=self.session) as client:
                # use asyncio.gather to parallelize deletion
                await asyncio.gather(*[
                    client.delete(bucket=bucket_name, object_name=file_name) for file_name in file_names
                ])
        except Exception:
            logger.exception("GoogleCloudStorage Batch Delete Error", bucket=bucket_name, filenames=file_names)
            if raise_exception_on_failure:
                raise

        end_ns = time_ns()

        logger.info(
            "GoogleCloudStorage Batch Delete",
            bucket=bucket_name,
            filenames=file_names,
            duration_ms=(end_ns - start_ns) / 1_000_000,
        )

    async def update_file_deletion_time(
        self, filename: str, new_time: datetime, bucket_name: str, *, raise_exception_on_failure=False
    ) -> None:
        # interesting
        if new_time > GCS_MAX_DATETIME_LIMIT:
            logger.error(
                "GoogleCloudStorage Exceeds Max Time",
                bucket=bucket_name,
                new_time=new_time,
            )
            msg = "Datetime exceeds GoogleCloudStorage maximum limit"
            raise ValueError(msg)

        start_ns = time_ns()

        try:
            async with Storage(session=self.session) as client:
                # Update custom time metadata
                # GCS uses customTime field in metadata
                await client.patch_metadata(
                    bucket=bucket_name,
                    object_name=filename,
                    metadata={
                        "customTime": new_time.isoformat(),
                    },
                )

                end_ns = time_ns()

                logger.info(
                    "GoogleCloudStorage Update Deletion Time",
                    bucket=bucket_name,
                    filename=filename,
                    new_time=new_time,
                    duration_ms=(end_ns - start_ns) / 1_000_000,
                )

        except Exception:
            logger.exception(
                "GoogleCloudStorage Update Deletion Time Error", filename=filename, bucket_name=bucket_name
            )
            if raise_exception_on_failure:
                raise

    # Helper function for migration
    async def migrate_anonymous_file(
        self, filename: str, bucket_name: str, *, raise_exception_on_failure=False
    ) -> None:
        logger.info(
            "GoogleCloudStorage Migrate User",
            bucket=bucket_name,
            filename=filename,
        )
        # GCS doesn't allow unsetting custom time, instead we're setting it to the furthest time possible
        await self.update_file_deletion_time(
            filename,
            GCS_MAX_DATETIME_LIMIT,
            bucket_name=bucket_name,
            raise_exception_on_failure=raise_exception_on_failure,
        )
