"""initial_schema

Revision ID: 202d63cb1c33
Revises: 
Create Date: 2026-03-17 00:56:42.952019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202d63cb1c33'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    Initial schema: tables already exist in the database,
    this migration just marks the current state.
    """
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
