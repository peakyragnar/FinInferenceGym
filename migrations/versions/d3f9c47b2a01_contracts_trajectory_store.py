"""Stage 3: contracts table — the trajectory store with real Contracts.

The trajectory store from DESIGN.md #8: every forecast + action + score
preserved in SFT-fit format for year-2 own-model training. Phase 1 NEW
stored Contracts in-memory only; this migration adds the Postgres home.

One row per Contract. Denormalized scalar fields for query convenience
(ticker, horizon, signal_class_id, agent_id, decision_time, action_type)
plus the full v5 Contract serialized as JSONB for round-trip via pydantic.

Realized returns are NOT stored here — they're computed on demand from
equity_prices via fingym.data.queries.equity_returns. Per-signal-class
reliability (the Forecast Ledger view) is computed at query time over
the contracts table joined to realized returns.

Revision ID: d3f9c47b2a01
Revises: c8d7e2a91f44
Create Date: 2026-05-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d3f9c47b2a01"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "c8d7e2a91f44"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "contracts",
        # Identity
        sa.Column("contract_id", postgresql.UUID(as_uuid=False), nullable=False),
        # Timing
        sa.Column("decision_time", sa.TIMESTAMP(timezone=True), nullable=False),
        # Identity continued
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        # Subject — denormalized for query convenience; also in the Contract JSON
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("horizon", sa.Text(), nullable=False),
        sa.Column("signal_class_id", sa.Text(), nullable=False),
        sa.Column("thesis_category", sa.Text()),
        # Action (denormalized)
        sa.Column("recommended_action_type", sa.Text(), nullable=False),
        sa.Column("recommended_size", sa.Numeric()),
        sa.Column("recommended_expression", sa.Text()),
        sa.Column("recommended_direction", sa.Text()),
        sa.Column("recommended_underlying", sa.Text()),
        sa.Column("no_action_reason", sa.Text()),
        # Forecast distribution (denormalized for fast aggregation)
        sa.Column(
            "forecast_distribution",
            postgresql.JSONB(),
            nullable=False,
            comment="map of bucket_label -> probability; sums to 1, no zeros (Cromwell)",
        ),
        # Full Contract for round-trip via pydantic
        sa.Column("contract_json", postgresql.JSONB(), nullable=False),
        # Provenance
        sa.Column(
            "data_sources_used",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("contract_id"),
        sa.CheckConstraint(
            "recommended_action_type IN ('trade', 'no_action')",
            name="contracts_action_type_check",
        ),
    )
    op.create_index("idx_contracts_decision_time", "contracts", ["decision_time"])
    op.create_index("idx_contracts_ticker_time", "contracts", ["ticker", "decision_time"])
    op.create_index("idx_contracts_signal_class", "contracts", ["signal_class_id"])
    op.create_index("idx_contracts_agent", "contracts", ["agent_id"])
    op.create_index("idx_contracts_horizon_time", "contracts", ["horizon", "decision_time"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_contracts_horizon_time", table_name="contracts")
    op.drop_index("idx_contracts_agent", table_name="contracts")
    op.drop_index("idx_contracts_signal_class", table_name="contracts")
    op.drop_index("idx_contracts_ticker_time", table_name="contracts")
    op.drop_index("idx_contracts_decision_time", table_name="contracts")
    op.drop_table("contracts")
