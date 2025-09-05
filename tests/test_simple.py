from src import db


def test_db(dbc: db.Client):
    result = dbc.message.get("123")
    assert result is None
