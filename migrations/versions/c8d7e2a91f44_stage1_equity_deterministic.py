"""Stage 1: deterministic equity data tables.

Creates the five deterministic-only tables that Stage 1 of real_data_ingest.md
populates from Massive Developer tier:

  - equity_prices            — daily OHLCV (split-adjusted; Massive default)
  - corporate_actions_splits — split events
  - corporate_actions_dividends — cash dividend events
  - tickers                  — universe reference, active + delisted
  - ipos                     — IPO listing events

Each follows the long-table pattern: simple PK, no inferred fields, no
curation choices. Pure vendor numeric/categorical facts.

See real_data_ingest.md "Stage 1" for full design and gating criteria.

Revision ID: c8d7e2a91f44
Revises: 7a3c81f4d029
Create Date: 2026-05-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8d7e2a91f44"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "7a3c81f4d029"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # tickers — universe reference. active=False rows are delisted.
    op.create_table(
        "tickers",
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("name", sa.Text()),
        sa.Column("market", sa.Text()),
        sa.Column("primary_exchange", sa.Text()),
        sa.Column("ticker_type", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("delisted_utc", sa.TIMESTAMP(timezone=True)),
        sa.Column("cik", sa.Text()),
        sa.Column("composite_figi", sa.Text()),
        sa.Column("share_class_figi", sa.Text()),
        sa.Column("last_updated_utc", sa.TIMESTAMP(timezone=True)),
        sa.Column("currency_name", sa.Text()),
        sa.Column("locale", sa.Text()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("ticker", "snapshot_date"),
    )

    # equity_prices — split-adjusted daily OHLCV.
    # PIT note: as_known = the trading day's close timestamp; daily prices
    # don't revise in practice, so vintage stays 1.
    op.create_table(
        "equity_prices",
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("as_known", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric()),
        sa.Column("high", sa.Numeric()),
        sa.Column("low", sa.Numeric()),
        sa.Column("close", sa.Numeric()),
        sa.Column("volume", sa.BigInteger()),
        sa.Column("vwap", sa.Numeric()),
        sa.Column("transactions", sa.Integer()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("vintage", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("ticker", "as_of", "vintage"),
    )
    op.create_index("idx_equity_prices_as_of", "equity_prices", ["as_of"])

    # corporate_actions_splits
    op.create_table(
        "corporate_actions_splits",
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=False),
        sa.Column("split_from", sa.Numeric(), nullable=False),
        sa.Column("split_to", sa.Numeric(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("ticker", "ex_date"),
    )

    # corporate_actions_dividends
    op.create_table(
        "corporate_actions_dividends",
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=False),
        sa.Column("declaration_date", sa.Date()),
        sa.Column("record_date", sa.Date()),
        sa.Column("pay_date", sa.Date()),
        sa.Column("cash_amount", sa.Numeric(), nullable=False),
        sa.Column("dividend_type", sa.Text()),
        sa.Column("frequency", sa.Integer()),
        sa.Column("currency", sa.Text()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # A ticker can have multiple dividend events on the same ex_date
        # (rare; differing declaration dates). Compound key.
        sa.PrimaryKeyConstraint("ticker", "ex_date", "cash_amount"),
    )

    # ipos
    op.create_table(
        "ipos",
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("ipo_date", sa.Date(), nullable=False),
        sa.Column("final_issue_price", sa.Numeric()),
        sa.Column("shares_outstanding", sa.BigInteger()),
        sa.Column("issuer_name", sa.Text()),
        sa.Column("primary_exchange", sa.Text()),
        sa.Column("ipo_status", sa.Text()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("ticker", "ipo_date"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ipos")
    op.drop_table("corporate_actions_dividends")
    op.drop_table("corporate_actions_splits")
    op.drop_index("idx_equity_prices_as_of", table_name="equity_prices")
    op.drop_table("equity_prices")
    op.drop_table("tickers")
