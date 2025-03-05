import re
import typing
from collections.abc import Sequence

import puremagic


def match_mime_type(file_mime_type: str, matching_mime_type: str):
    matches = re.search(matching_mime_type, file_mime_type)
    return matches is not None


def check_is_file_in_allowed_file_types(file_stream: typing.IO[bytes], allowed_file_types: Sequence[str]):
    # This is partially here to allow us to keep testing without using real files!
    if len(allowed_file_types) == 0:
        return True

    potential_mime_types = puremagic.magic_stream(file_stream)

    return any(
        any(match_mime_type(mime_type.mime_type, allowed_file_type) for mime_type in potential_mime_types)
        for allowed_file_type in allowed_file_types
    )
