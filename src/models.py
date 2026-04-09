from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class ImageMixin:
    """Base mixin for images"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
