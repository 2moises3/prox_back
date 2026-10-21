"""
PROXVEL Backend - Engine Config Model.
Parámetros ajustables del motor de recomendación (un solo registro gestionable).
Reemplaza la sección "config" de destinos.json.
"""

from sqlalchemy import Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class EngineConfig(Base, TimestampMixin):
    __tablename__ = "engine_config"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Peso del componente ABSA en la afinidad (tesis Fase 3: 0.25; el resto va a intereses).
    alpha_absa: Mapped[float] = mapped_column(Float, default=0.25, server_default="0.25")
    # DEPRECADOS (fórmula previa al alineamiento con la tesis). No los usa el motor.
    alpha_afinidad: Mapped[float] = mapped_column(Float, default=0.85)
    beta_intereses: Mapped[float] = mapped_column(Float, default=0.15)
    # Peso del contexto en el score final: afinidad + beta_contexto * (C - 0.5).
    beta_contexto: Mapped[float] = mapped_column(Float, default=0.30)
    w_clima: Mapped[float] = mapped_column(Float, default=0.5)
    w_aforo: Mapped[float] = mapped_column(Float, default=0.5)
    factor_tolerancia_baja: Mapped[float] = mapped_column(Float, default=1.0)
    factor_tolerancia_media: Mapped[float] = mapped_column(Float, default=0.65)
    factor_tolerancia_alta: Mapped[float] = mapped_column(Float, default=0.35)
