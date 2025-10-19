"""Admin endpoints for managing tenants, users, and channels."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...api.schemas import (
    TenantCreate, TenantUpdate, TenantResponse,
    UserCreate, UserUpdate, UserResponse,
    ChannelCreate, ChannelUpdate, ChannelResponse,
    PaginationParams, PaginatedResponse
)
from ...api.dependencies import require_admin, require_owner
from ...models.user import User
from ...services.tenant_service import TenantService
from ...services.user_service import UserService
from ...services.channel_service import ChannelService

router = APIRouter(prefix="/admin", tags=["admin"])


# Tenant management
@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner)
) -> TenantResponse:
    """Create a new tenant."""
    tenant_service = TenantService(db)
    
    try:
        tenant = await tenant_service.create_tenant(tenant_data.model_dump())
        return TenantResponse.model_validate(tenant)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create tenant: {str(e)}"
        )


@router.get("/tenants", response_model=PaginatedResponse)
async def list_tenants(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner)
) -> PaginatedResponse:
    """List all tenants."""
    tenant_service = TenantService(db)
    
    try:
        result = await tenant_service.list_tenants(
            page=pagination.page,
            size=pagination.size
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tenants: {str(e)}"
        )


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_owner)
) -> TenantResponse:
    """Get tenant by ID."""
    tenant_service = TenantService(db)
    
    try:
        tenant = await tenant_service.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        return TenantResponse.model_validate(tenant)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant: {str(e)}"
        )


# User management
@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> UserResponse:
    """Create a new user."""
    user_service = UserService(db)
    
    try:
        user = await user_service.create_user(
            tenant_id=current_user.tenant_id,
            user_data=user_data.model_dump()
        )
        return UserResponse.model_validate(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create user: {str(e)}"
        )


@router.get("/users", response_model=PaginatedResponse)
async def list_users(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> PaginatedResponse:
    """List users in current tenant."""
    user_service = UserService(db)
    
    try:
        result = await user_service.list_users(
            tenant_id=current_user.tenant_id,
            page=pagination.page,
            size=pagination.size
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


# Channel management
@router.post("/channels", response_model=ChannelResponse)
async def create_channel(
    channel_data: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> ChannelResponse:
    """Create a new channel."""
    channel_service = ChannelService(db)
    
    try:
        channel = await channel_service.create_channel(
            tenant_id=current_user.tenant_id,
            channel_data=channel_data.model_dump()
        )
        return ChannelResponse.model_validate(channel)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create channel: {str(e)}"
        )


@router.get("/channels", response_model=PaginatedResponse)
async def list_channels(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> PaginatedResponse:
    """List channels in current tenant."""
    channel_service = ChannelService(db)
    
    try:
        result = await channel_service.list_channels(
            tenant_id=current_user.tenant_id,
            page=pagination.page,
            size=pagination.size
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list channels: {str(e)}"
        )


@router.get("/channels/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> ChannelResponse:
    """Get channel by ID."""
    channel_service = ChannelService(db)
    
    try:
        channel = await channel_service.get_channel(
            tenant_id=current_user.tenant_id,
            channel_id=channel_id
        )
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        return ChannelResponse.model_validate(channel)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get channel: {str(e)}"
        )


@router.put("/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: str,
    channel_data: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> ChannelResponse:
    """Update channel by ID."""
    channel_service = ChannelService(db)
    
    try:
        channel = await channel_service.update_channel(
            tenant_id=current_user.tenant_id,
            channel_id=channel_id,
            channel_data=channel_data.model_dump(exclude_unset=True)
        )
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        return ChannelResponse.model_validate(channel)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update channel: {str(e)}"
        )


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Delete channel by ID."""
    channel_service = ChannelService(db)
    
    try:
        success = await channel_service.delete_channel(
            tenant_id=current_user.tenant_id,
            channel_id=channel_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        return {"success": True, "message": "Channel deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete channel: {str(e)}"
        )

