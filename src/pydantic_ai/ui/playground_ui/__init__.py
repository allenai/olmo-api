"""Playground protocol adapter for Pydantic AI agents.

This module provides classes for integrating Pydantic AI agents with the Playground input/output.
"""

from ._adapter import PlaygroundUIAdapter
from ._event_stream import PlaygroundUIEventStream

__all__ = [
    "PlaygroundUIAdapter",
    "PlaygroundUIEventStream",
]
