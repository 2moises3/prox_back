"""
PROXVEL Backend - Destination Month Context Model.
Contexto mensual (clima + aforo) por destino que consume el motor.
Mapea 1:1 con la sección "meses" de destinos.json.
Reemplaza clima_scores.csv + aforo_scores_mensual.csv para el motor.
"""

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DestinationMonthContext(Base):
    __tablename__ = "destination_month_context"
    __table_args__ = (
        UniqueConstraint("destination_id", "month", name="uq_dest_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destinations.destination_id"), index=True
    )
    month: Mapped[int] = mapped_column(Integer, index=True)

    clima_score: Mapped[float | None] = mapped_column(Float)
    clima_nivel: Mapped[str | None] = mapped_column(String)
    temp_prom: Mapped[float | None] = mapped_column(Float)
    pp: Mapped[float | None] = mapped_column(Float)

    aforo_score: Mapped[float | None] = mapped_column(Float)
    aforo_nivel: Mapped[str | None] = mapped_column(String)
    aforo_fuente: Mapped[str | None] = mapped_column(String)
    # Score de clima por preferencia declarada: {"calido": 0.85, "frio": 0.44, ...}
    clima_por_preferencia: Mapped[dict | None] = mapped_column(JSON)
    # Score de aforo ya personalizado por tolerancia: {"baja": 0.13, "media": 0.30, "alta": 0.57}
    aforo_por_tolerancia: Mapped[dict | None] = mapped_column(JSON)

    # Textos y datos de la tesis (Fase 4) para mostrar en el detalle del destino.
    clima_explicacion: Mapped[str | None] = mapped_column(Text)
    clima_riesgo: Mapped[str | None] = mapped_column(String)   # p. ej. "calor, lluvia"
    aforo_explicacion: Mapped[str | None] = mapped_column(Text)
    visitantes_medios: Mapped[float | None] = mapped_column(Float)
