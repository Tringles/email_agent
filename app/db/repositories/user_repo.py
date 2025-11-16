"""User repository for database operations."""

from loguru import logger
from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by OAuth email.

        Args:
            email: OAuth email address

        Returns:
            User object or None
        """
        return self.db.query(User).filter(User.oauth_email == email).first()

    def get_user_by_oauth_provider_user_id(
        self,
        provider: str,
        provider_user_id: str
    ) -> Optional[User]:
        """
        Get user by OAuth provider and provider user ID.

        Args:
            provider: OAuth provider (e.g., 'google', 'naver')
            provider_user_id: Provider's user ID

        Returns:
            User object or None
        """
        return self.db.query(User).filter(
            User.oauth_provider == provider,
            User.oauth_provider_user_id == provider_user_id
        ).first()

    def create_user(self, user_data: dict) -> User:
        """
        Create a new user.

        Args:
            user_data: User data dictionary

        Returns:
            Created User object
        """
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Created user: {user.id} ({user.oauth_email})")
        return user

    def update_user(self, user: User, **kwargs) -> User:
        """
        Update user record.

        Args:
            user: User object to update
            **kwargs: Fields to update

        Returns:
            Updated User object
        """
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Updated user: {user.id}")
        return user

    def deactivate_user(self, user_id: int) -> Optional[User]:
        """
        Deactivate user account.

        Args:
            user_id: User ID

        Returns:
            Updated User object or None
        """
        user = self.get_user_by_id(user_id)
        if user:
            user.is_active = False
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Deactivated user: {user_id}")
        return user

    def activate_user(self, user_id: int) -> Optional[User]:
        """
        Activate user account.

        Args:
            user_id: User ID

        Returns:
            Updated User object or None
        """
        user = self.get_user_by_id(user_id)
        if user:
            user.is_active = True
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Activated user: {user_id}")
        return user

