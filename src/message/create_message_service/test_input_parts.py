from src.constants import MOLMO_2_TRACKING_FRAME_RATE
from src.message.create_message_request import Molmo2PointPart
from src.message.create_message_service.input_parts import map_input_parts


def test_map_input_parts_formats_molmo_2_points_when_present():
    content = "Man in the red shirt"
    result = map_input_parts([Molmo2PointPart(x=380, y=1000, time=2.8)], content)

    assert (
        result
        == f'Object tracking: <points coords="2.8 1 380 1000">object</points> formatted as <points coords="t id x y">label</points>, {MOLMO_2_TRACKING_FRAME_RATE} FPS rate. {content}'
    )


def test_map_input_parts_returns_when_no_parts_present():
    content = "Man in the red shirt"
    result = map_input_parts(None, content)

    assert result == content
