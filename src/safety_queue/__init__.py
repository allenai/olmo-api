import dramatiq
from dramatiq.brokers.stub import StubBroker

from src.safety_queue.set_up_safety_queue import set_up_safety_queue as set_up_safety_queue

# Dramatiq requires the broker to be set up before the actors are set up. This uses a StubBroker to set one and set_up_safety_queue sets up the correct one when called
# https://github.com/Bogdanp/dramatiq/pull/762
dramatiq.set_broker(StubBroker())
