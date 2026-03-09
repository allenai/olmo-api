# Import actor modules so dramatiq can discover them
import api.thread.chat.safety.safety_checkers.google_video_safety_checker  # noqa: F401
from api.safety_queue import setup_safety_queue

setup_safety_queue()
