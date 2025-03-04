import typing
from collections.abc import Sequence

import filetype


def check_is_file_in_allowed_file_types(file_stream: typing.IO[bytes], allowed_file_types: Sequence[str]):
    file_type_matchers: set = set()

    for allowed_file_type in allowed_file_types:
        if allowed_file_type == "image/*":
            file_type_matchers.update(filetype.image_matchers)

        elif allowed_file_type == "audio/*":
            file_type_matchers.update(filetype.audio_matchers)

        elif allowed_file_type == "video/*":
            file_type_matchers.update(filetype.video_matchers)

        elif allowed_file_type == "font/*":
            file_type_matchers.update(filetype.font_matchers)

        elif allowed_file_type == "document/*":
            file_type_matchers.update(filetype.document_matchers)

        elif allowed_file_type == "archive/*":
            file_type_matchers.update(filetype.archive_matchers)

        elif allowed_file_type == "application/*":
            file_type_matchers.update(filetype.application_matchers)

        else:
            matcher = next(file_type for file_type in filetype.types if allowed_file_type == file_type.MIME)
            if matcher is not None:
                file_type_matchers.add(matcher)

    matched_file_type = filetype.match(file_stream, file_type_matchers)

    return matched_file_type is not None
