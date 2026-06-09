"""
PROXVEL Backend - Base ORM Model.
Modelo base declarativo para SQLAlchemy.
"""

from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Clase base para todos los modelos ORM."""
    
    pass


class TimestampMixin:
    """Mixin para agregar created_at y updated_at a los modelos."""
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )
