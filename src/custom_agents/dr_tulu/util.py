import uuid


def create_call_id():
    return str(uuid.uuid4())[:8]
