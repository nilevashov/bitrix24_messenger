"""Update channel type enum values

Revision ID: 493453022412
Revises: 1f7f8d18be67
Create Date: 2025-10-19 22:25:02.345061

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '493453022412'
down_revision = '1f7f8d18be67'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update enum values for channel type
    op.execute("ALTER TYPE channeltype RENAME VALUE 'tg' TO 'telegram'")
    op.execute("ALTER TYPE channeltype RENAME VALUE 'wa' TO 'whatsapp'")


def downgrade() -> None:
    # Revert enum values for channel type
    op.execute("ALTER TYPE channeltype RENAME VALUE 'telegram' TO 'tg'")
    op.execute("ALTER TYPE channeltype RENAME VALUE 'whatsapp' TO 'wa'")
