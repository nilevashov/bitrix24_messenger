"""Bitrix24 integration endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...api.schemas import BitrixOAuthRequest, BitrixOAuthResponse
from ...api.dependencies import require_admin
from ...models.user import User
from ...services.bitrix_service import BitrixService

router = APIRouter(prefix="/bitrix", tags=["bitrix"])


@router.post("/install", response_model=BitrixOAuthResponse)
async def install_bitrix_app(
    oauth_request: BitrixOAuthRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> BitrixOAuthResponse:
    """Install Bitrix24 application and get OAuth tokens."""
    bitrix_service = BitrixService(db)
    
    try:
        tokens = await bitrix_service.install_app(
            tenant_id=current_user.tenant_id,
            code=oauth_request.code,
            domain=oauth_request.domain,
            member_id=oauth_request.member_id
        )
        
        return BitrixOAuthResponse(
            success=True,
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens.get("expires_in")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to install Bitrix app: {str(e)}"
        )


@router.post("/refresh-token")
async def refresh_bitrix_token(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> BitrixOAuthResponse:
    """Refresh Bitrix24 OAuth token."""
    bitrix_service = BitrixService(db)
    
    try:
        tokens = await bitrix_service.refresh_token(current_user.tenant_id)
        
        return BitrixOAuthResponse(
            success=True,
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens.get("expires_in")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.get("/status")
async def get_bitrix_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> dict:
    """Get Bitrix24 integration status."""
    bitrix_service = BitrixService(db)
    
    try:
        status_info = await bitrix_service.get_integration_status(current_user.tenant_id)
        return status_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )

