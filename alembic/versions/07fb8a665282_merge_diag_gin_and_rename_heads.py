"""merge_diag_gin_and_rename_heads

Revision ID: 07fb8a665282
Revises: d2e4f6a8b1c3, e2a5b7c1d3f9
Create Date: 2026-04-28 11:28:49.459757

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '07fb8a665282'
down_revision: Union[str, Sequence[str], None] = ('d2e4f6a8b1c3', 'e2a5b7c1d3f9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
