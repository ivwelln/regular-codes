import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountStatus(enum.StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    steam_id: Mapped[str] = mapped_column(String(32), unique=True)
    username: Mapped[str] = mapped_column(String(32))
    encrypted_session: Mapped[str] = mapped_column(Text)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, native_enum=False, length=16), default=AccountStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
