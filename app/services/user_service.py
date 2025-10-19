"""User service for authentication and user management."""

from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

from ..core.config import settings
from ..models.user import User, UserRole, UserStatus
from ..api.schemas import PaginatedResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Service for user management and authentication."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def create_user(
        self, 
        username: str,
        email: str,
        password_hash: str,
        tenant_id: UUID,
        role: str = "admin",
        status: str = "active"
    ) -> User:
        """Create a new user."""
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            tenant_id=tenant_id,
            role=UserRole(role),
            status=UserStatus(status)
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Optional[User]:
        """Update user."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        # Hash password if provided
        if "password" in user_data:
            user_data["password_hash"] = pwd_context.hash(user_data["password"])
            del user_data["password"]
        
        for key, value in user_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def list_users(
        self, 
        tenant_id: UUID, 
        page: int = 1, 
        size: int = 20
    ) -> PaginatedResponse:
        """List users with pagination."""
        offset = (page - 1) * size
        
        # Get total count
        count_result = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id)
        )
        total = len(count_result.scalars().all())
        
        # Get paginated results
        result = await self.db.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .offset(offset)
            .limit(size)
        )
        users = result.scalars().all()
        
        return PaginatedResponse(
            items=[user for user in users],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(
            minutes=settings.security.access_token_expire_minutes
        )
        
        to_encode = {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "email": user.email,
            "role": user.role.value,
            "exp": expire
        }
        
        return jwt.encode(
            to_encode, 
            settings.security.secret_key, 
            algorithm=settings.security.algorithm
        )
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(
            days=settings.security.refresh_token_expire_days
        )
        
        to_encode = {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "type": "refresh",
            "exp": expire
        }
        
        return jwt.encode(
            to_encode,
            settings.security.secret_key,
            algorithm=settings.security.algorithm
        )
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_by_email(email)
        if not user:
            return None
        
        if not user.password_hash:
            return None
        
        if not self.verify_password(password, user.password_hash):
            return None
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.db.commit()
        
        return user

