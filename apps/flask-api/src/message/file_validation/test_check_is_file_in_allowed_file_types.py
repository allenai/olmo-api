import os

from src.message.file_validation.check_is_file_in_allowed_file_types import (
    check_is_file_in_allowed_file_types,
)


def test_returns_true_when_passed_a_png():
    with open(os.path.join(os.path.dirname(__file__), "test-small-png.png"), "rb") as f:
        png_result = check_is_file_in_allowed_file_types(f, allowed_file_types=["image/png"])
        assert png_result is True

        star_result = check_is_file_in_allowed_file_types(file_stream=f, allowed_file_types=["image/*"])
        assert star_result is True

        multi_result = check_is_file_in_allowed_file_types(
            file_stream=f, allowed_file_types=["application.pdf", "image/png"]
        )
        assert multi_result is True


def test_returns_false_when_passed_a_png():
    with open(os.path.join(os.path.dirname(__file__), "test-small-png.png"), "rb") as f:
        mp4_result = check_is_file_in_allowed_file_types(f, ["video/mp4"])
        assert mp4_result is False

        application_result = check_is_file_in_allowed_file_types(f, ["application/*"])
        assert application_result is False


def test_returns_true_when_passed_a_pdf():
    with open(os.path.join(os.path.dirname(__file__), "test-small-pdf.pdf"), "rb") as f:
        png_result = check_is_file_in_allowed_file_types(f, allowed_file_types=["application/pdf"])
        assert png_result is True

        star_result = check_is_file_in_allowed_file_types(f, allowed_file_types=["application/*"])
        assert star_result is True

        multi_result = check_is_file_in_allowed_file_types(
            file_stream=f, allowed_file_types=["image/png", "application.pdf"]
        )
        assert multi_result is True


def test_returns_false_when_passed_a_pdf():
    with open(os.path.join(os.path.dirname(__file__), "test-small-pdf.pdf"), "rb") as f:
        mp4_result = check_is_file_in_allowed_file_types(f, ["video/mp4"])
        assert mp4_result is False

        application_result = check_is_file_in_allowed_file_types(f, ["image/*"])
        assert application_result is False
