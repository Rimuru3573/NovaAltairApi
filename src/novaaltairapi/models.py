from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from novaaltairapi.db import Base

class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    referred_by_user: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.username"), nullable=True, default=None)
    is_referral_rewarded: Mapped[bool] = mapped_column(Boolean, default=False)
    refresh_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    keys: Mapped[list["Keys"]] = relationship(back_populates="users", cascade="all, delete-orphan",)


class Keys(Base):
    __tablename__ = "keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(128), unique=True)
    sub_id: Mapped[str] = mapped_column(String(32), index=True)
    sub_link: Mapped[str] = mapped_column(Text)
    expiry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payment_id: Mapped[str | None] = mapped_column(String(128), default=None)

    user_username: Mapped[str] = mapped_column(ForeignKey("users.username", ondelete="CASCADE"))
    users: Mapped["Users"] = relationship(back_populates="keys")
