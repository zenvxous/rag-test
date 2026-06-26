"""enable vector extension

Revision ID: 5ec48671c2ee
Revises: 63e994d1f9cd
Create Date: 2026-06-25 15:13:25.551000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ec48671c2ee'
down_revision: Union[str, Sequence[str], None] = '63e994d1f9cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
