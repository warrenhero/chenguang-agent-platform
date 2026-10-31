"""add prompt version unique constraint

Revision ID: 34ec95133419
Revises: 29197e22dc03
Create Date: 2026-10-31 21:50:22.119819

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '34ec95133419'
down_revision: Union[str, Sequence[str], None] = '29197e22dc03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        "uq_prompt_versions_prompt_version",
        "prompt_versions",
        ["prompt_id", "version"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_prompt_versions_prompt_version",
        "prompt_versions",
        type_="unique",
    )
