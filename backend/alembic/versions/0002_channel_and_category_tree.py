"""migration 0002: channel_name on videos + hierarchical categories

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("channel_name", sa.String(length=200), nullable=True))
    op.add_column(
        "categories",
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_categories_parent_id", "categories", "categories", ["parent_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_categories_parent_id"), "categories", ["parent_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_categories_parent_id"), table_name="categories")
    op.drop_constraint("fk_categories_parent_id", "categories", type_="foreignkey")
    op.drop_column("categories", "parent_id")
    op.drop_column("videos", "channel_name")
