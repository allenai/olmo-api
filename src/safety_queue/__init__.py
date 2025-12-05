from src.safety_queue.set_up_safety_queue import set_up_safety_queue

# Dramatiq requires the broker to be set up before the actors are set up. This is an easy way to do that. We should changethis in the future.
set_up_safety_queue()
