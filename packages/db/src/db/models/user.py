import datetime

from sqlalchemy import DateTime, PrimaryKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.object_id import new_id_generator

from .base import Base


class User(Base, kw_only=True):
    __tablename__ = "olmo_user"
    __table_args__ = (PrimaryKeyConstraint("id", name="olmo_user_pkey"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True, default_factory=new_id_generator("user"))
    client: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    terms_accepted_date: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    acceptance_revoked_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(True), nullable=True)
    data_collection_accepted_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(True), nullable=True)
    data_collection_acceptance_revoked_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(True), nullable=True
    )
    media_collection_accepted_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(True), nullable=True)
    media_collection_acceptance_revoked_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(True), nullable=True
    )
