from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # A user-owned loan history has no business meaning after the user is removed.
    loans: Mapped[list["Loan"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    author: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # A loan references one physical catalog entry, so its history is deleted with that book.
    loans: Mapped[list["Loan"]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
    )


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), index=True, default="borrowed", nullable=False)
    borrowed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="loans")
    book: Mapped[Book] = relationship(back_populates="loans")
