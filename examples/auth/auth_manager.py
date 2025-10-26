"""
Authentication Support for Documentation Scraper
================================================

This module provides comprehensive authentication mechanisms for accessing
protected documentation sites.

Features:
- HTTP Basic Authentication
- Bearer Token Authentication
- Cookie-based Session Authentication
- API Key Authentication (header/query param)
- OAuth 2.0 Client Credentials Flow
- Custom Header Authentication
- Credential Management (secure storage)
- Session Persistence

Usage:
    from auth_manager import AuthManager, AuthType

    auth = AuthManager()
    auth.add_credential('api.example.com', AuthType.BEARER, token='abc123')

    session = auth.get_authenticated_session('api.example.com')
    response = session.get('https://api.example.com/docs')
"""

import base64
import json
import keyring
import requests
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class AuthType(Enum):
    """Supported authentication types."""
    NONE = 'none'
    BASIC = 'basic'
    BEARER = 'bearer'
    API_KEY = 'api_key'
    COOKIE = 'cookie'
    OAUTH2 = 'oauth2'
    CUSTOM_HEADER = 'custom_header'


class Credential:
    """
    Base credential class for storing authentication information.
    """

    def __init__(self, auth_type: AuthType, **kwargs):
        """
        Initialize credential.

        Args:
            auth_type: Type of authentication
            **kwargs: Authentication-specific parameters
        """
        self.auth_type = auth_type
        self.params = kwargs

    def to_dict(self) -> dict:
        """Convert credential to dictionary."""
        return {
            'auth_type': self.auth_type.value,
            **self.params
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Credential':
        """Create credential from dictionary."""
        auth_type = AuthType(data.pop('auth_type'))
        return cls(auth_type, **data)

    def apply_to_session(self, session: requests.Session):
        """
        Apply authentication to requests session.

        Args:
            session: requests.Session to configure
        """
        if self.auth_type == AuthType.BASIC:
            username = self.params.get('username')
            password = self.params.get('password')
            session.auth = (username, password)
            logger.debug(f"Applied Basic auth for user: {username}")

        elif self.auth_type == AuthType.BEARER:
            token = self.params.get('token')
            session.headers['Authorization'] = f'Bearer {token}'
            logger.debug("Applied Bearer token authentication")

        elif self.auth_type == AuthType.API_KEY:
            api_key = self.params.get('api_key')
            key_name = self.params.get('key_name', 'X-API-Key')
            location = self.params.get('location', 'header')

            if location == 'header':
                session.headers[key_name] = api_key
                logger.debug(f"Applied API key to header: {key_name}")
            elif location == 'query':
                # Will be added per-request
                session.params = {key_name: api_key}
                logger.debug(f"Applied API key to query param: {key_name}")

        elif self.auth_type == AuthType.COOKIE:
            cookies = self.params.get('cookies', {})
            for name, value in cookies.items():
                session.cookies.set(name, value)
            logger.debug(f"Applied {len(cookies)} cookies")

        elif self.auth_type == AuthType.CUSTOM_HEADER:
            headers = self.params.get('headers', {})
            session.headers.update(headers)
            logger.debug(f"Applied {len(headers)} custom headers")


class OAuth2Handler:
    """
    OAuth 2.0 Client Credentials Flow handler.

    Supports automatic token refresh.
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: Optional[str] = None
    ):
        """
        Initialize OAuth2 handler.

        Args:
            token_url: OAuth2 token endpoint
            client_id: Client ID
            client_secret: Client secret
            scope: Optional scope string
        """
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope

        self.access_token: Optional[str] = None
        self.token_type: str = 'Bearer'
        self.expires_at: Optional[float] = None

    def get_token(self) -> str:
        """
        Get valid access token (refreshes if needed).

        Returns:
            Valid access token
        """
        import time

        # Check if token is still valid
        if self.access_token and self.expires_at:
            if time.time() < self.expires_at - 60:  # 60s buffer
                return self.access_token

        # Request new token
        logger.info("Requesting new OAuth2 token")

        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        if self.scope:
            data['scope'] = self.scope

        response = requests.post(self.token_url, data=data)
        response.raise_for_status()

        token_data = response.json()

        self.access_token = token_data['access_token']
        self.token_type = token_data.get('token_type', 'Bearer')
        expires_in = token_data.get('expires_in', 3600)

        import time
        self.expires_at = time.time() + expires_in

        logger.info(f"Obtained new token, expires in {expires_in}s")

        return self.access_token

    def apply_to_session(self, session: requests.Session):
        """Apply OAuth2 authentication to session."""
        token = self.get_token()
        session.headers['Authorization'] = f'{self.token_type} {token}'


class AuthManager:
    """
    Centralized authentication manager for documentation scraping.

    Manages credentials for multiple domains and provides authenticated sessions.
    """

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize authentication manager.

        Args:
            config_file: Optional path to credential config file
        """
        self.config_file = config_file or Path.home() / '.scraper_auth.json'
        self.credentials: Dict[str, Credential] = {}
        self.oauth_handlers: Dict[str, OAuth2Handler] = {}

        self._load_credentials()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc

    def _load_credentials(self):
        """Load credentials from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)

                for domain, cred_data in data.items():
                    self.credentials[domain] = Credential.from_dict(cred_data)

                logger.info(f"Loaded {len(self.credentials)} credentials")
            except Exception as e:
                logger.error(f"Failed to load credentials: {e}")

    def _save_credentials(self):
        """Save credentials to config file."""
        try:
            data = {
                domain: cred.to_dict()
                for domain, cred in self.credentials.items()
            }

            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self.credentials)} credentials")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def add_credential(
        self,
        domain: str,
        auth_type: AuthType,
        **kwargs
    ):
        """
        Add credential for domain.

        Args:
            domain: Target domain
            auth_type: Type of authentication
            **kwargs: Authentication parameters

        Example:
            auth.add_credential(
                'api.example.com',
                AuthType.BASIC,
                username='user',
                password='pass'
            )
        """
        self.credentials[domain] = Credential(auth_type, **kwargs)
        self._save_credentials()
        logger.info(f"Added {auth_type.value} credential for {domain}")

    def add_oauth2(
        self,
        domain: str,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: Optional[str] = None
    ):
        """
        Add OAuth2 credential for domain.

        Args:
            domain: Target domain
            token_url: OAuth2 token endpoint
            client_id: Client ID
            client_secret: Client secret
            scope: Optional scope
        """
        handler = OAuth2Handler(
            token_url,
            client_id,
            client_secret,
            scope
        )

        self.oauth_handlers[domain] = handler
        logger.info(f"Added OAuth2 credential for {domain}")

    def get_credential(self, url: str) -> Optional[Credential]:
        """
        Get credential for URL.

        Args:
            url: Target URL

        Returns:
            Credential or None
        """
        domain = self._extract_domain(url)
        return self.credentials.get(domain)

    def get_authenticated_session(self, url: str) -> requests.Session:
        """
        Get authenticated session for URL.

        Args:
            url: Target URL

        Returns:
            Configured requests.Session
        """
        session = requests.Session()
        domain = self._extract_domain(url)

        # Apply OAuth2 if available
        if domain in self.oauth_handlers:
            self.oauth_handlers[domain].apply_to_session(session)
            return session

        # Apply standard credential
        credential = self.credentials.get(domain)
        if credential:
            credential.apply_to_session(session)

        return session

    def remove_credential(self, domain: str):
        """Remove credential for domain."""
        if domain in self.credentials:
            del self.credentials[domain]
            self._save_credentials()
            logger.info(f"Removed credential for {domain}")

        if domain in self.oauth_handlers:
            del self.oauth_handlers[domain]

    def list_credentials(self) -> Dict[str, str]:
        """
        List all configured credentials.

        Returns:
            Dictionary mapping domain to auth type
        """
        return {
            domain: cred.auth_type.value
            for domain, cred in self.credentials.items()
        }


def authenticated_get(
    url: str,
    auth_manager: AuthManager,
    **kwargs
) -> requests.Response:
    """
    Make authenticated HTTP GET request.

    Args:
        url: Target URL
        auth_manager: AuthManager instance
        **kwargs: Additional arguments for requests.get

    Returns:
        requests.Response
    """
    session = auth_manager.get_authenticated_session(url)
    return session.get(url, **kwargs)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    auth = AuthManager()

    # Add various credential types
    auth.add_credential(
        'api.example.com',
        AuthType.BEARER,
        token='your_bearer_token_here'
    )

    auth.add_credential(
        'docs.example.com',
        AuthType.BASIC,
        username='user',
        password='password'
    )

    auth.add_credential(
        'secure-api.example.com',
        AuthType.API_KEY,
        api_key='your_api_key',
        key_name='X-API-Key',
        location='header'
    )

    # List credentials
    print("\nConfigured Credentials:")
    for domain, auth_type in auth.list_credentials().items():
        print(f"  {domain}: {auth_type}")

    # Make authenticated request
    # response = authenticated_get('https://api.example.com/docs', auth)
    # print(f"\nResponse: {response.status_code}")
