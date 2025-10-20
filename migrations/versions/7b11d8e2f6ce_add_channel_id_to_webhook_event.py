"""Add channel reference to webhook_event

Revision ID: 7b11d8e2f6ce
Revises: 1f7f8d18be67
Create Date: 2025-10-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b11d8e2f6ce'
down_revision = '1f7f8d18be67'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('webhook_event', sa.Column('channel_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_webhook_event_channel_id',
        'webhook_event',
        'channel',
        ['channel_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_webhook_event_channel_id', 'webhook_event', type_='foreignkey')
    op.drop_column('webhook_event', 'channel_id')
