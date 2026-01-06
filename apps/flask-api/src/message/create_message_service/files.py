import os
from collections.abc import Sequence
from dataclasses import dataclass

from werkzeug.datastructures import FileStorage

from src.config.get_config import get_config
from src.message.GoogleCloudStorage import GoogleCloudStorage


@dataclass
class FileUploadResult:
    file_url: str
    file_storage: FileStorage


def upload_request_files(
    files: Sequence[FileStorage] | None,
    message_id: str,
    storage_client: GoogleCloudStorage,
    root_message_id: str,
) -> list[FileUploadResult]:
    if files is None or len(files) == 0:
        return []

    file_results: list[FileUploadResult] = []

    for i, file in enumerate(files):
        file_extension = os.path.splitext(file.filename)[1] if file.filename is not None else ""

        # We don't want to save filenames since we're not safety checking them for dangerous or personal info
        filename = f"{root_message_id}/{message_id}-{i}{file_extension}"

        cfg = get_config()

        upload_response = storage_client.upload_content(
            filename=filename,
            content=file,
            bucket_name=cfg.google_cloud_services.storage_bucket,
            make_file_public=True,
        )

        # since we read from the file we need to rewind it so the next consumer can read it
        file.stream.seek(0)

        file_results.append(FileUploadResult(file_url=upload_response.public_url, file_storage=file))

    return file_results
