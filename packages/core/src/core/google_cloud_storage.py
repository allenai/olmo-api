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

        span = trace.get_current_span()
        span.set_attributes({
            "bucket": bucket_name,
            "object_name": filename,
            "content_type": content_type or "None",
            "make_file_public": make_file_public,
        })

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
            "gcs.upload_content.complete",
            bucket=bucket_name,
            filename=filename,
            duration_ms=(end_ns - start_ns) / 1_000_000,
        )

        # Construct URLs
        public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"
        storage_path = f"gs://{bucket_name}/{filename}"

        return UploadResponse(public_url=public_url, storage_path=storage_path)

    @tracer.start_as_current_span("GoogleCloudStorageService/delete_file")
    async def delete_file(self, filename: str, bucket_name: str, *, raise_exception_on_failure=False) -> None:
        start_ns = time_ns()

        span = trace.get_current_span()
        span.set_attributes({
            "bucket": bucket_name,
            "object_name": filename,
        })

        try:
            async with Storage(session=self.session) as client:
                # return value?
                await client.delete(bucket=bucket_name, object_name=filename)

        except Exception as e:
            span.record_exception(e)
            logger.exception("gcs.delete_file.error", bucket=bucket_name, filename=filename)
            if raise_exception_on_failure:
                raise

        end_ns = time_ns()

        logger.info(
            "gcs.delete_file.complete",
            bucket=bucket_name,
            filename=filename,
            duration_ms=(end_ns - start_ns) / 1_000_000,
        )

    @tracer.start_as_current_span("GoogleCloudStorageService/delete_multiple_files_by_url")
    async def delete_multiple_files_by_url(
        self, file_urls: list[str], bucket_name: str, *, raise_exception_on_failure=False
    ) -> None:
        start_ns = time_ns()

        span = trace.get_current_span()
        span.set_attributes({
            "bucket": bucket_name,
            "file_urls": file_urls,
        })

        base_url = f"https://storage.googleapis.com/{bucket_name}/"
        file_names = [re.sub(base_url, "", file_url) for file_url in file_urls]

        try:
            async with Storage(session=self.session) as client:
                # use asyncio.gather to parallelize deletion
                await asyncio.gather(*[
                    client.delete(bucket=bucket_name, object_name=file_name) for file_name in file_names
                ])
        except Exception as e:
            span.record_exception(e)
            logger.exception("gcs.delete_multiple_files_by_url.error", bucket=bucket_name, filenames=file_names)
            if raise_exception_on_failure:
                raise

        end_ns = time_ns()

        logger.info(
            "gcs.delete_multiple_files_by_url.complete",
            bucket=bucket_name,
            filenames=file_names,
            duration_ms=(end_ns - start_ns) / 1_000_000,
        )

    @tracer.start_as_current_span("GoogleCloudStorageService/update_file_deletion_time")
    async def update_file_deletion_time(
        self, filename: str, new_time: datetime, bucket_name: str, *, raise_exception_on_failure=False
    ) -> None:
        # interesting
        if new_time > GCS_MAX_DATETIME_LIMIT:
            logger.error(
                "gcs.update_file_deletion_time.excedes_max_time_error",
                bucket=bucket_name,
                new_time=new_time,
            )
            msg = "Datetime exceeds GoogleCloudStorage maximum limit"
            raise ValueError(msg)

        start_ns = time_ns()

        span = trace.get_current_span()
        span.set_attributes({
            "bucket": bucket_name,
            "filename": filename,
            "new_time": str(new_time),
        })

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
                    "gcs.update_file_deletion_time.complete",
                    bucket=bucket_name,
                    filename=filename,
                    new_time=new_time,
                    duration_ms=(end_ns - start_ns) / 1_000_000,
                )

        except Exception as e:
            span.record_exception(e)
            logger.exception("gcs.update_file_deletion_time.error", filename=filename, bucket_name=bucket_name)
            if raise_exception_on_failure:
                raise

    # Helper function for migration
    @tracer.start_as_current_span("GoogleCloudStorageService/migrate_anonymous_file")
    async def migrate_anonymous_file(
        self, filename: str, bucket_name: str, *, raise_exception_on_failure=False
    ) -> None:
        logger.info(
            "gcs.migrate_anonymous_file",
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

    @tracer.start_as_current_span("GoogleCloudStorageService/delete_prefix")
    async def delete_prefix(self, prefix: str, bucket_name: str, *, raise_exception_on_failure: bool = False) -> None:
        start_ns = time_ns()
        file_names: list[str] = []

        span = trace.get_current_span()
        span.set_attributes({
            "prefix": prefix,
            "bucket_name": bucket_name,
        })

        try:
            async with Storage(session=self.session) as client:
                bucket = client.get_bucket(bucket_name)
                file_names = await bucket.list_blobs(prefix=prefix)
                span.set_attribute("file_names", file_names)

                await asyncio.gather(
                    *[client.delete(bucket=bucket_name, object_name=name) for name in file_names],
                    return_exceptions=True,
                )
        except Exception as e:
            span.record_exception(e)
            logger.exception("gcs.delete_prefix.error", bucket=bucket_name, filenames=file_names)
            if raise_exception_on_failure:
                raise

        end_ns = time_ns()

        logger.info(
            "gcs.delete_prefix.complete",
            bucket=bucket_name,
            filenames=file_names,
            duration_ms=(end_ns - start_ns) / 1_000_000,
        )
