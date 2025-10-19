"""Pydantic schemas for API requests and responses."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

from ..models.user import UserRole, UserStatus
from ..models.channel import ChannelType, ChannelState
from ..models.message import MessageDirection, MessageStatus
from ..models.dialog import DialogStatus


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = {
        "from_attributes": True,
        "use_enum_values": True
    }


# Authentication schemas
class LoginRequest(BaseSchema):
    """Login request schema."""
    username: str
    password: str


class LoginResponse(BaseSchema):
    """Login response schema."""
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


# User schemas
class UserBase(BaseSchema):
    email: str
    role: UserRole = UserRole.VIEWER
    status: UserStatus = UserStatus.ACTIVE


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseSchema):
    email: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


class UserResponse(UserBase):
    id: UUID
    tenant_id: UUID
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Tenant schemas
class TenantBase(BaseSchema):
    name: str
    domain: str
    bitrix_portal: str
    openlines_enabled: bool = True
    timeline_enabled: bool = True


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseSchema):
    name: Optional[str] = None
    domain: Optional[str] = None
    bitrix_portal: Optional[str] = None
    openlines_enabled: Optional[bool] = None
    timeline_enabled: Optional[bool] = None


class TenantResponse(TenantBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Channel schemas
class ChannelBase(BaseSchema):
    type: ChannelType
    name: str
    config: Dict[str, Any] = Field(default_factory=dict)
    external_channel_id: Optional[str] = None


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseSchema):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    external_channel_id: Optional[str] = None


class ChannelResponse(ChannelBase):
    id: UUID
    tenant_id: UUID
    state: ChannelState
    created_at: datetime
    updated_at: datetime


class ChannelListResponse(BaseSchema):
    """Response for channel list."""
    items: List[ChannelResponse]


# Message schemas
class MessageBase(BaseSchema):
    direction: MessageDirection
    messenger: str
    chat_id: str
    external_msg_id: str
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_meta: Dict[str, Any] = Field(default_factory=dict)


class MessageCreate(MessageBase):
    dialog_id: UUID
    channel_id: UUID


class MessageResponse(MessageBase):
    id: UUID
    tenant_id: UUID
    dialog_id: UUID
    channel_id: UUID
    dedup_key: str
    status: MessageStatus
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    fail_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Dialog schemas
class DialogBase(BaseSchema):
    messenger: str
    chat_id: str
    status: DialogStatus = DialogStatus.OPEN


class DialogCreate(DialogBase):
    channel_id: UUID


class DialogResponse(DialogBase):
    id: UUID
    tenant_id: UUID
    channel_id: UUID
    bitrix_dialog_id: Optional[str] = None
    opened_at: datetime
    closed_at: Optional[datetime] = None
    operator_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Webhook schemas
class WebhookEnvelope(BaseSchema):
    """Webhook envelope for incoming events."""
    source: str
    event_type: str
    payload: Dict[str, Any]
    dedup_key: str
    signature: Optional[str] = None


class WebhookResponse(BaseSchema):
    """Webhook response."""
    success: bool
    message: Optional[str] = None
    event_id: Optional[UUID] = None


# Bitrix integration schemas
class BitrixOAuthRequest(BaseSchema):
    """Bitrix OAuth installation request."""
    code: str
    domain: str
    member_id: str


class BitrixOAuthResponse(BaseSchema):
    """Bitrix OAuth installation response."""
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None


# Contact mapping schemas
class ContactMapBase(BaseSchema):
    messenger: str
    chat_id: str
    phone: Optional[str] = None
    username: Optional[str] = None
    bitrix_contact_id: Optional[str] = None
    bitrix_lead_id: Optional[str] = None


class ContactMapCreate(ContactMapBase):
    pass


class ContactMapResponse(ContactMapBase):
    id: UUID
    tenant_id: UUID
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Media schemas
class MediaMeta(BaseSchema):
    """Media metadata."""
    filename: str
    content_type: str
    size: int
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None  # For audio/video


class MediaUploadResponse(BaseSchema):
    """Media upload response."""
    url: str
    media_id: str
    meta: MediaMeta


# Error schemas
class ErrorResponse(BaseSchema):
    """Error response schema."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


# Pagination schemas
class PaginationParams(BaseSchema):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    
    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int) -> int:
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int
    pages: int

