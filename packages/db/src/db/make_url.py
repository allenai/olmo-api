from sqlalchemy import URL


def make_url(conninfo) -> URL:
    return (
        make_url(conninfo)
        .set(drivername="postgresql+psycopg")
        .update_query_dict({"autosave": "conservative"}, append=True)
    )
