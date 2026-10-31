"""add unique constraint to model_providers name

Revision ID: 6a70aef19267
Revises: f60f5baf56e3
Create Date: 2026-10-31 20:29:29.322713

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a70aef19267'
down_revision: Union[str, Sequence[str], None] = 'f60f5baf56e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        "uq_model_providers_name", "model_providers", ["name"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_model_providers_name", "model_providers", type_="unique"
    )
