from typing import TYPE_CHECKING, Final

from db.models.input_parts import InputPart, PointPartType

if TYPE_CHECKING:
    from collections.abc import Sequence

MOLMO_2_TRACKING_FRAME_RATE: Final[int] = 2


def _format_molmo_2_input_points(input_parts: Sequence[InputPart], content: str) -> str:
    # Currently only getting the first input point since we're only sending one for molmo 2
    point_part = next((part for part in input_parts if part.type == PointPartType.MOLMO_2_INPUT_POINT), None)

    if point_part:
        point_string = f'<points coords="{point_part.time} 1 {point_part.x} {point_part.y}">{point_part.label}</points>'
        return f'Object tracking: {point_string} formatted as <points coords="t id x y">label</points>, {MOLMO_2_TRACKING_FRAME_RATE} FPS rate. {content}'

    return content


def map_input_parts(input_parts: Sequence[InputPart] | None, initial_content: str) -> str:
    if not input_parts:
        return initial_content

    return _format_molmo_2_input_points(input_parts, initial_content)
