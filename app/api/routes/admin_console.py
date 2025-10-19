"""Admin console API endpoints."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...api.dependencies import require_admin, get_current_user
from ...api.schemas import LoginRequest, LoginResponse
from ...models.user import User
from uuid import UUID
from ...services.admin_service import AdminService
from ...services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-console"])


# Temporary function for development - get default tenant
async def get_default_tenant_id(db: AsyncSession) -> UUID:
    """Get default tenant ID for development."""
    from ...models.tenant import Tenant
    from sqlalchemy import select
    
    result = await db.execute(select(Tenant).limit(1))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        # Create default tenant for development
        tenant = Tenant(
            name="Default Tenant",
            domain="localhost",
            bitrix_portal="localhost.bitrix24.com",
            openlines_enabled=True,
            timeline_enabled=True
        )
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
    
    return tenant.id


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """Login endpoint for admin console."""
    from ...core.config import settings
    from jose import jwt
    from datetime import datetime, timedelta
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    user_service = UserService(db)
    
    # Get or create default admin user
    user = await user_service.get_by_username(login_data.username)
    if not user:
        # Create default admin user
        tenant_id = await get_default_tenant_id(db)
        hashed_password = pwd_context.hash(login_data.password)
        
        user = await user_service.create_user(
            username=login_data.username,
            email=f"{login_data.username}@localhost",
            password_hash=hashed_password,
            tenant_id=tenant_id,
            role="admin",
            status="active"
        )
    else:
        # Verify password
        if not pwd_context.verify(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password"
            )
    
    # Create JWT token
    access_token_expires = timedelta(hours=24)
    access_token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.utcnow() + access_token_expires,
            "username": user.username,
            "role": user.role.value
        },
        settings.security.secret_key,
        algorithm=settings.security.algorithm
    )
    
    return LoginResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "tenant_id": str(user.tenant_id)
        }
    )


@router.get("/", response_class=HTMLResponse)
async def admin_console():
    """Serve admin console HTML."""
    with open("app/admin/static/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Get dashboard statistics."""
    admin_service = AdminService(db)
    
    try:
        stats = await admin_service.get_dashboard_stats(current_user.tenant_id)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.get("/channels")
async def get_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Get channels for current tenant."""
    admin_service = AdminService(db)
    
    try:
        channels = await admin_service.get_channels(current_user.tenant_id)
        return {"items": channels}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get channels: {str(e)}"
        )


@router.post("/channels")
async def create_channel(
    channel_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Create a new channel."""
    # Debug: print to console directly
    print(f"DEBUG: Endpoint received channel_data: {channel_data}")
    logger.info(f"Endpoint received channel_data: {channel_data}")
    admin_service = AdminService(db)
    
    try:
        result = await admin_service.create_channel(current_user.tenant_id, channel_data)
        
        # Debug: check what was actually saved
        from sqlalchemy import select
        from ...models.channel import Channel
        saved_channel = await db.execute(
            select(Channel).where(Channel.tenant_id == current_user.tenant_id).order_by(Channel.created_at.desc()).limit(1)
        )
        latest_channel = saved_channel.scalar_one_or_none()
        if latest_channel:
            print(f"DEBUG: Latest channel config: {latest_channel.config}")
        
        return {"success": result}
    except Exception as e:
        print(f"DEBUG: Error creating channel: {str(e)}")
        logger.error(f"Error creating channel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create channel: {str(e)}"
        )


@router.post("/channels/{channel_id}/toggle")
async def toggle_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Toggle channel status."""
    admin_service = AdminService(db)
    
    try:
        result = await admin_service.toggle_channel(current_user.tenant_id, channel_id)
        return {"success": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle channel: {str(e)}"
        )


@router.put("/channels/{channel_id}")
async def update_channel(
    channel_id: str,
    channel_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Update channel."""
    admin_service = AdminService(db)
    
    try:
        result = await admin_service.update_channel(current_user.tenant_id, channel_id, channel_data)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        return {"success": True, "message": "Channel updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update channel: {str(e)}"
        )


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Delete channel."""
    admin_service = AdminService(db)
    
    try:
        result = await admin_service.delete_channel(current_user.tenant_id, channel_id)
        if not result:
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


@router.get("/debug/channels")
async def debug_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Debug endpoint to see raw channel data from database."""
    from sqlalchemy import select, text
    from ...models.channel import Channel
    
    try:
        # Get raw data from database
        result = await db.execute(
            select(Channel).where(Channel.tenant_id == current_user.tenant_id)
        )
        channels = result.scalars().all()
        
        debug_data = []
        for channel in channels:
            debug_data.append({
                "id": str(channel.id),
                "name": channel.name,
                "type": channel.type.value if channel.type else None,
                "config": channel.config,
                "config_type": type(channel.config).__name__,
                "config_repr": repr(channel.config)
            })
        
        return {"channels": debug_data}
    except Exception as e:
        return {"error": str(e)}


@router.post("/debug/test")
async def debug_test(
    test_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Debug endpoint to test channel creation logic."""
    from ...models.channel import ChannelType, ChannelState, Channel
    from ...services.admin_service import AdminService
    
    # Test the same logic as in AdminService.create_channel
    type_mapping = {
        "telegram": ChannelType.TELEGRAM,
        "whatsapp": ChannelType.WHATSAPP
    }
    
    channel_type = type_mapping.get(test_data.get("type", "").lower())
    if not channel_type:
        return {"error": f"Unsupported channel type: {test_data.get('type')}"}
    
    # Prepare config based on channel type
    config = {}
    if channel_type == ChannelType.TELEGRAM and "bot_token" in test_data:
        config["bot_token"] = test_data["bot_token"]
    
    # Test AdminService.create_channel
    admin_service = AdminService(db)
    
    try:
        result = await admin_service.create_channel(current_user.tenant_id, test_data)
        
        # Check what was actually saved
        from sqlalchemy import select
        saved_channel = await db.execute(
            select(Channel).where(Channel.tenant_id == current_user.tenant_id).order_by(Channel.created_at.desc()).limit(1)
        )
        latest_channel = saved_channel.scalar_one_or_none()
        
        return {
            "input_data": test_data,
            "channel_type": channel_type.value if channel_type else None,
            "config": config,
            "admin_service_result": result,
            "saved_channel_id": str(latest_channel.id) if latest_channel else None,
            "saved_config": latest_channel.config if latest_channel else None
        }
    except Exception as e:
        return {
            "error": str(e),
            "input_data": test_data,
            "config": config
        }


@router.get("/messages")
async def get_messages(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Get recent messages."""
    admin_service = AdminService(db)
    
    try:
        messages = await admin_service.get_recent_messages(current_user.tenant_id, limit)
        return {"items": messages}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}"
        )


@router.get("/bitrix/config")
async def get_bitrix_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Get Bitrix24 configuration."""
    admin_service = AdminService(db)
    
    try:
        config = await admin_service.get_bitrix_config(current_user.tenant_id)
        return config
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Bitrix24 config: {str(e)}"
        )


@router.post("/bitrix/config")
async def save_bitrix_config(
    config_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Save Bitrix24 configuration."""
    admin_service = AdminService(db)
    
    try:
        result = await admin_service.save_bitrix_config(current_user.tenant_id, config_data)
        return {"success": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save Bitrix24 config: {str(e)}"
        )


@router.post("/settings")
async def save_settings(
    settings_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Save system settings."""
    admin_service = AdminService(db)
    
    try:
        result = await admin_service.save_settings(current_user.tenant_id, settings_data)
        return {"success": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save settings: {str(e)}"
        )
