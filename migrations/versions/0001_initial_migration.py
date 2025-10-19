"""Initial migration

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    
    # Create tenant table
    op.create_table('tenant',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('bitrix_portal', sa.String(length=255), nullable=False),
        sa.Column('bitrix_app_id', sa.String(length=255), nullable=True),
        sa.Column('bitrix_secret', sa.String(length=255), nullable=True),
        sa.Column('bitrix_oauth_access', sa.Text(), nullable=True),
        sa.Column('bitrix_oauth_refresh', sa.Text(), nullable=True),
        sa.Column('oauth_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('openlines_enabled', sa.Boolean(), nullable=False),
        sa.Column('timeline_enabled', sa.Boolean(), nullable=False),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain')
    )
    
    # Create user table
    op.create_table('user',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('role', sa.Enum('owner', 'admin', 'manager', 'viewer', 'service', name='userrole'), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', name='userstatus'), nullable=False),
        sa.Column('mfa_secret', sa.String(length=255), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_user_tenant_id'), 'user', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=False)
    
    # Create channel table
    op.create_table('channel',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.Enum('tg', 'wa', 'viber', 'instagram', name='channeltype'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('state', sa.Enum('active', 'inactive', 'error', name='channelstate'), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('external_channel_id', sa.String(length=255), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_channel_tenant_id'), 'channel', ['tenant_id'], unique=False)
    
    # Create contact_map table
    op.create_table('contact_map',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('messenger', sa.Enum('telegram', 'whatsapp', 'viber', 'instagram', name='messengertype'), nullable=False),
        sa.Column('chat_id', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('bitrix_contact_id', sa.String(length=50), nullable=True),
        sa.Column('bitrix_lead_id', sa.String(length=50), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contact_map_tenant_messenger_chat', 'contact_map', ['tenant_id', 'messenger', 'chat_id'], unique=False)
    op.create_index('ix_contact_map_tenant_phone', 'contact_map', ['tenant_id', 'phone'], unique=False)
    op.create_index('ix_contact_map_tenant_username', 'contact_map', ['tenant_id', 'username'], unique=False)
    op.create_index('ix_contact_map_tenant_bitrix_contact', 'contact_map', ['tenant_id', 'bitrix_contact_id'], unique=False)
    
    # Create deal_link table
    op.create_table('deal_link',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bitrix_contact_id', sa.String(length=50), nullable=False),
        sa.Column('bitrix_deal_id', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_deal_link_tenant_contact', 'deal_link', ['tenant_id', 'bitrix_contact_id'], unique=False)
    op.create_index('ix_deal_link_tenant_deal', 'deal_link', ['tenant_id', 'bitrix_deal_id'], unique=False)
    op.create_index('ix_deal_link_tenant_contact_active', 'deal_link', ['tenant_id', 'bitrix_contact_id', 'is_active'], unique=False)
    
    # Create dialog table
    op.create_table('dialog',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('messenger', sa.String(length=50), nullable=False),
        sa.Column('chat_id', sa.String(length=255), nullable=False),
        sa.Column('bitrix_dialog_id', sa.String(length=50), nullable=True),
        sa.Column('status', sa.Enum('open', 'closed', 'paused', name='dialogstatus'), nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('operator_user_id', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_dialog_tenant_channel', 'dialog', ['tenant_id', 'channel_id'], unique=False)
    op.create_index('ix_dialog_tenant_messenger_chat', 'dialog', ['tenant_id', 'messenger', 'chat_id'], unique=False)
    op.create_index('ix_dialog_tenant_status', 'dialog', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_dialog_tenant_bitrix_dialog', 'dialog', ['tenant_id', 'bitrix_dialog_id'], unique=False)
    
    # Create message table
    op.create_table('message',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dialog_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('direction', sa.Enum('in', 'out', name='messagedirection'), nullable=False),
        sa.Column('messenger', sa.String(length=50), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', sa.String(length=255), nullable=False),
        sa.Column('external_msg_id', sa.String(length=255), nullable=False),
        sa.Column('dedup_key', sa.String(length=255), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('media_url', sa.String(length=500), nullable=True),
        sa.Column('media_meta', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.Enum('received', 'queued', 'sent', 'delivered', 'read', 'failed', name='messagestatus'), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fail_reason', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedup_key')
    )
    op.create_index('ix_message_tenant_dialog', 'message', ['tenant_id', 'dialog_id'], unique=False)
    op.create_index('ix_message_tenant_external_msg', 'message', ['tenant_id', 'external_msg_id'], unique=False)
    op.create_index('ix_message_tenant_dedup_key', 'message', ['tenant_id', 'dedup_key'], unique=False)
    op.create_index('ix_message_tenant_status', 'message', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_message_tenant_messenger_chat', 'message', ['tenant_id', 'messenger', 'chat_id'], unique=False)
    op.create_index('ix_message_tenant_created_at', 'message', ['tenant_id', 'created_at'], unique=False)
    
    # Create webhook_event table
    op.create_table('webhook_event',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.Enum('channel', 'bitrix', name='webhooksource'), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('dedup_key', sa.String(length=255), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedup_key')
    )
    op.create_index('ix_webhook_event_tenant_source', 'webhook_event', ['tenant_id', 'source'], unique=False)
    op.create_index('ix_webhook_event_tenant_dedup_key', 'webhook_event', ['tenant_id', 'dedup_key'], unique=False)
    op.create_index('ix_webhook_event_tenant_processed', 'webhook_event', ['tenant_id', 'processed_at'], unique=False)
    op.create_index('ix_webhook_event_tenant_created_at', 'webhook_event', ['tenant_id', 'created_at'], unique=False)
    
    # Create routing_rule table
    op.create_table('routing_rule',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('predicate', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('target', sa.Enum('openlines', 'timeline', name='routingtarget'), nullable=False),
        sa.Column('assign_strategy', sa.Enum('by_city', 'round_robin', 'fixed', name='assignstrategy'), nullable=False),
        sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('priority', sa.String(length=10), nullable=False),
        sa.Column('is_active', sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_routing_rule_tenant_id'), 'routing_rule', ['tenant_id'], unique=False)
    
    # Create audit_log table
    op.create_table('audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_log_tenant_actor', 'audit_log', ['tenant_id', 'actor_user_id'], unique=False)
    op.create_index('ix_audit_log_tenant_action', 'audit_log', ['tenant_id', 'action'], unique=False)
    op.create_index('ix_audit_log_tenant_created_at', 'audit_log', ['tenant_id', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_log')
    op.drop_table('routing_rule')
    op.drop_table('webhook_event')
    op.drop_table('message')
    op.drop_table('dialog')
    op.drop_table('deal_link')
    op.drop_table('contact_map')
    op.drop_table('channel')
    op.drop_table('user')
    op.drop_table('tenant')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS userstatus')
    op.execute('DROP TYPE IF EXISTS channeltype')
    op.execute('DROP TYPE IF EXISTS channelstate')
    op.execute('DROP TYPE IF EXISTS messengertype')
    op.execute('DROP TYPE IF EXISTS dialogstatus')
    op.execute('DROP TYPE IF EXISTS messagedirection')
    op.execute('DROP TYPE IF EXISTS messagestatus')
    op.execute('DROP TYPE IF EXISTS webhooksource')
    op.execute('DROP TYPE IF EXISTS routingtarget')
    op.execute('DROP TYPE IF EXISTS assignstrategy')
