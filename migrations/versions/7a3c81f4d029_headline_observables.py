"""Create headline_observables table.

The macro time-series substrate. One row per (series_id, as_of, vintage).
Vintage defaults to 1 in v1 (current revised values from FRED). Future
ingest passes that pull first-print values via ALFRED will append rows
with higher vintage numbers.

Per DESIGN.md / TECHNICAL.md, this table is the Market-State Baseline's
input table AND is readable by the AI Core. The Baseline reads a narrow
7-series subset at read time. The architectural isolation is on the
Baseline's processed forecast (hidden from the AI Core), NOT on the raw
data here.

Revision ID: 7a3c81f4d029
Revises: 34760aee56bf
Create Date: 2026-05-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a3c81f4d029"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "34760aee56bf"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "headline_observables",
        sa.Column("series_id", sa.Text(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("as_known", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("vintage", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("series_id", "as_of", "vintage"),
    )
    op.create_index(
        "idx_headline_observables_as_of",
        "headline_observables",
        ["as_of"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_headline_observables_as_of", table_name="headline_observables")
    op.drop_table("headline_observables")
