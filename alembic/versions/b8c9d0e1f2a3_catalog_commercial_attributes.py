"""catalog_commercial_attributes

Catálogo turístico más comercial: se eliminan los atributos heredados de MINCETUR que no aportan
al viajero ni al motor, y se agregan duración recomendada, cómo llegar, dificultad y sitio oficial.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DROPPED = [
    "official_name", "department", "province", "district", "type", "subtype", "hierarchy",
    "experience_type", "geofence_radius_m", "cover_image_url",
    "gallery_image_1", "gallery_image_2", "gallery_image_3", "gallery_image_4",
    "image_source", "image_license_note",
    "official_source_name", "official_source_code", "official_source_url",
    "secondary_source_name", "secondary_source_code", "secondary_source_url", "map_source",
]


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("tourism_catalog")}

    for name, col in (
        ("recommended_duration", sa.Column("recommended_duration", sa.String(), nullable=True)),
        ("how_to_get", sa.Column("how_to_get", sa.Text(), nullable=True)),
        ("difficulty", sa.Column("difficulty", sa.String(), nullable=True)),
        ("official_website", sa.Column("official_website", sa.String(), nullable=True)),
    ):
        if name not in existing:
            op.add_column("tourism_catalog", col)

    for name in DROPPED:
        if name in existing:
            op.drop_column("tourism_catalog", name)


def downgrade() -> None:
    # Los datos eliminados no se pueden recuperar; solo se restaura la estructura.
    for name in ("official_website", "difficulty", "how_to_get", "recommended_duration"):
        op.drop_column("tourism_catalog", name)
    for name in DROPPED:
        op.add_column("tourism_catalog", sa.Column(
            name, sa.Integer() if name == "hierarchy" else sa.Float() if name == "geofence_radius_m" else sa.String(),
            nullable=True))
