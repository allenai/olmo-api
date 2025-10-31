"""
Type alias for uploaded files.

This module provides a type alias for file uploads that works with both
Flask (werkzeug.datastructures.FileStorage) and FastAPI (via conversion).
"""

from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from werkzeug.datastructures import FileStorage


class UploadedFile(FileStorage):
    """
    Wrapper around FileStorage that works with Pydantic V2.

    This class inherits from FileStorage and adds Pydantic schema support,
    allowing it to be used in Pydantic models with arbitrary_types_allowed=True.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Provide Pydantic V2 core schema for FileStorage"""
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls._serialize,
                when_used='json'
            ),
        )

    @classmethod
    def _validate(cls, v: Any) -> "UploadedFile":
        """Validate that the value is a FileStorage object"""
        if isinstance(v, FileStorage):
            # If it's already a FileStorage, wrap it as UploadedFile
            if isinstance(v, UploadedFile):
                return v
            # Copy FileStorage attributes to UploadedFile
            uploaded = UploadedFile(
                stream=v.stream,
                filename=v.filename,
                name=v.name,
                content_type=v.content_type,
                content_length=v.content_length,
                headers=v.headers,
            )
            return uploaded
        raise ValueError("Must be a FileStorage object")

    @staticmethod
    def _serialize(v: "UploadedFile") -> str:
        """Serialize FileStorage to just the filename for JSON"""
        return v.filename or "unknown"
