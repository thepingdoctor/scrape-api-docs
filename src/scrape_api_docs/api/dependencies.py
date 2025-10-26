"""
FastAPI Dependencies
====================

Dependency injection for API endpoints.
"""

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[str]:
    """
    Verify API key authentication.

    Args:
        api_key: API key from header

    Returns:
        Verified API key or None if not provided
    """
    if not api_key:
        return None

    # TODO: Implement actual API key verification
    # For now, accept any non-empty key

    return api_key


async def verify_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Optional[str]:
    """
    Verify Bearer token authentication.

    Args:
        credentials: Bearer token credentials

    Returns:
        Verified token or None if not provided
    """
    if not credentials:
        return None

    # TODO: Implement actual token verification (JWT, etc.)
    # For now, accept any token

    return credentials.credentials


async def get_current_user(
    api_key: Optional[str] = Depends(verify_api_key),
    token: Optional[str] = Depends(verify_bearer_token)
) -> Optional[dict]:
    """
    Get current authenticated user.

    Checks both API key and Bearer token authentication.

    Returns:
        User information or None if not authenticated
    """
    if api_key:
        # TODO: Look up user by API key
        return {"user_id": "api_key_user", "auth_method": "api_key"}

    if token:
        # TODO: Decode JWT and extract user info
        return {"user_id": "token_user", "auth_method": "bearer"}

    return None


def require_authentication(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """
    Require authenticated user.

    Raises 401 if user is not authenticated.

    Args:
        user: Current user from dependency

    Returns:
        User information

    Raises:
        HTTPException: If user is not authenticated
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user
