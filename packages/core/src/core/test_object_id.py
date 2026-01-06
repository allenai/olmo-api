from .object_id import NewID


def test_new_id():
    ids = [NewID("test") for _ in range(1000)]
    assert len(ids) == len(set(ids))
    assert all(id.startswith("test") for id in ids)
