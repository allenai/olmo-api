from . import obj

def test_new_id():
    ids = [obj.NewID("test") for _ in range(1000)]
    assert len(ids) == len(set(ids))
    assert all([id.startswith("test") for id in ids])

