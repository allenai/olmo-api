import os
from collections.abc import Sequence

from werkzeug.datastructures import FileStorage

from src.message.GoogleCloudStorage import GoogleCloudStorage


def upload_request_files(
    files: Sequence[FileStorage] | None,
    message_id: str,
    storage_client: GoogleCloudStorage,
    root_message_id: str,
    is_anonymous: bool = False,
) -> list[str] | None:
    if files is None or len(files) == 0:
        return None

    file_urls: list[str] = []

    for i, file in enumerate(files):
        file_extension = os.path.splitext(file.filename)[1] if file.filename is not None else ""

        # We don't want to save filenames since we're not safety checking them for dangerous or personal info
        filename = f"{root_message_id}/{message_id}-{i}{file_extension}"

        if file.content_type is None:
            file_url = storage_client.upload_content(
                filename=filename, content=file.stream.read(), is_anonymous=is_anonymous
            )
        else:
            file_url = storage_client.upload_content(
                filename=filename, content=file.stream.read(), content_type=file.content_type, is_anonymous=is_anonymous
            )

        # since we read from the file we need to rewind it so the next consumer can read it
        file.stream.seek(0)
        file_urls.append(file_url)

    return file_urls
