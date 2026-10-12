import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivationStatus(enum.StrEnum):
    ACTIVATED = "activated"
    REJECTED = "rejected"
    NOT_FOUND = "not_found"
    FAILED = "failed"


class Activation(Base):
    __tablename__ = "activations"
    __table_args__ = (UniqueConstraint("account_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    status: Mapped[ActivationStatus] = mapped_column(
        Enum(ActivationStatus, native_enum=False, length=16)
    )
    code: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
