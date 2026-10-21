"""legal_consent_reports_audit

Etapa legal: consentimiento registrado, reportes y ocultamiento de reseñas, y registro de auditoría.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-10-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    user_cols = {c["name"] for c in insp.get_columns("users")}
    if "accepted_terms_version" not in user_cols:
        op.add_column("users", sa.Column("accepted_terms_version", sa.String(20), nullable=True))
    if "accepted_terms_at" not in user_cols:
        op.add_column("users", sa.Column("accepted_terms_at", sa.DateTime(), nullable=True))

    review_cols = {c["name"] for c in insp.get_columns("reviews")}
    if "is_hidden" not in review_cols:
        op.add_column("reviews", sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()))

    tables = set(insp.get_table_names())
    if "review_reports" not in tables:
        op.create_table(
            "review_reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("review_id", sa.String(), sa.ForeignKey("reviews.review_id", ondelete="CASCADE"), nullable=False),
            sa.Column("reporter_user_id", sa.String(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("reason", sa.String(40), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("review_id", "reporter_user_id", name="uq_review_report_user"),
        )
        op.create_index("ix_review_reports_id", "review_reports", ["id"])
        op.create_index("ix_review_reports_review_id", "review_reports", ["review_id"])
        op.create_index("ix_review_reports_reporter_user_id", "review_reports", ["reporter_user_id"])
    if "audit_events" not in tables:
        op.create_table(
            "audit_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event", sa.String(80), nullable=False),
            sa.Column("user_id", sa.String(40), nullable=True),
            sa.Column("ip", sa.String(64), nullable=True),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_audit_events_id", "audit_events", ["id"])
        op.create_index("ix_audit_events_event", "audit_events", ["event"])
        op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
        op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("review_reports")
    op.drop_column("reviews", "is_hidden")
    op.drop_column("users", "accepted_terms_at")
    op.drop_column("users", "accepted_terms_version")
