"""initial

Revision ID: 34760aee56bf
Revises:
Create Date: 2026-05-14 17:05:35.497183

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic. The hex `revision` triggers
# detect-secrets's high-entropy-string check; the pragma silences that
# false positive.
revision: str = "34760aee56bf"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
