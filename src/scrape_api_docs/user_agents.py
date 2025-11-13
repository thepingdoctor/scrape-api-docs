"""
User Agent Management
====================

Provides a comprehensive library of user agent strings for different
browsers, devices, and personas to use when scraping websites.

Usage:
    from scrape_api_docs.user_agents import UserAgents, get_user_agent

    # Get a predefined user agent
    ua = get_user_agent('chrome_windows')
    
    # Get by category
    ua = get_user_agent('mobile_chrome_android')
    
    # List all available
    all_agents = UserAgents.get_all()
"""

from typing import Dict, List, Optional
from enum import Enum


class UserAgentCategory(str, Enum):
    """Categories of user agents."""
    DESKTOP_BROWSER = "desktop_browser"
    MOBILE_BROWSER = "mobile_browser"
    BOT = "bot"
    CUSTOM = "custom"
    DEFAULT = "default"


class UserAgents:
    """
    Comprehensive collection of user agent strings.
    
    Organized by browser type, operating system, and device category.
    """

    # Desktop Browsers - Chrome
    CHROME_WINDOWS = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    CHROME_MAC = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    CHROME_LINUX = (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Desktop Browsers - Firefox
    FIREFOX_WINDOWS = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
        "Gecko/20100101 Firefox/121.0"
    )
    
    FIREFOX_MAC = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) "
        "Gecko/20100101 Firefox/121.0"
    )
    
    FIREFOX_LINUX = (
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) "
        "Gecko/20100101 Firefox/121.0"
    )

    # Desktop Browsers - Safari
    SAFARI_MAC = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.1 Safari/605.1.15"
    )

    # Desktop Browsers - Edge
    EDGE_WINDOWS = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    )
    
    EDGE_MAC = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    )

    # Mobile Browsers - Chrome Mobile
    CHROME_ANDROID = (
        "Mozilla/5.0 (Linux; Android 13) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.6099.144 Mobile Safari/537.36"
    )
    
    CHROME_ANDROID_TABLET = (
        "Mozilla/5.0 (Linux; Android 13) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.6099.144 Safari/537.36"
    )

    # Mobile Browsers - Safari Mobile
    SAFARI_IPHONE = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.1 Mobile/15E148 Safari/604.1"
    )
    
    SAFARI_IPAD = (
        "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.1 Mobile/15E148 Safari/604.1"
    )

    # Mobile Browsers - Firefox Mobile
    FIREFOX_ANDROID = (
        "Mozilla/5.0 (Android 13; Mobile; rv:121.0) "
        "Gecko/121.0 Firefox/121.0"
    )

    # Search Engine Bots
    GOOGLEBOT = (
        "Mozilla/5.0 (compatible; Googlebot/2.1; "
        "+http://www.google.com/bot.html)"
    )
    
    GOOGLEBOT_SMARTPHONE = (
        "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.6099.144 Mobile Safari/537.36 "
        "(compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    )
    
    BINGBOT = (
        "Mozilla/5.0 (compatible; bingbot/2.0; "
        "+http://www.bing.com/bingbot.htm)"
    )
    
    DUCKDUCKBOT = (
        "DuckDuckBot/1.0; (+http://duckduckgo.com/duckduckbot.html)"
    )

    # Project Default
    SCRAPER_DEFAULT = "scrape-api-docs/0.1.0"

    # Legacy Browsers (for testing)
    IE11_WINDOWS = (
        "Mozilla/5.0 (Windows NT 10.0; Trident/7.0; rv:11.0) like Gecko"
    )

    # Metadata for each user agent
    METADATA = {
        'chrome_windows': {
            'name': 'Chrome (Windows)',
            'string': CHROME_WINDOWS,
            'category': UserAgentCategory.DESKTOP_BROWSER,
            'description': 'Latest Chrome on Windows 10/11'
        },
        'chrome_mac': {
            'name': 'Chrome (macOS)',
            'string': CHROME_MAC,
            'category': UserAgentCategory.DESKTOP_BROWSER,
            'description': 'Latest Chrome on macOS'
        },
        'chrome_linux': {
            'name': 'Chrome (Linux)',
            'string': CHROME_LINUX,
            'category': UserAgentCategory.DESKTOP_BROWSER,
            'description': 'Latest Chrome on Linux'
        },
        'firefox_windows': {
            'name': 'Firefox (Windows)',
            'string': FIREFOX_WINDOWS,
            'category': UserAgentCategory.DESKTOP_BROWSER,
            'description': 'Latest Firefox on Windows 10/11'
        },
        'firefox_mac': {
            'name': 'Firefox (macOS)',
            'string': FIREFOX_MAC,
            'category': UserAgentCategory.DESKTOP_BROWSER,
            'description': 'Latest Firefox on macOS'
        },
        'firefox_linux': {
            'name': 'Firefox (Linux)',
            'string': FIREFOX_LINUX,
            'category': UserAgentCategory.DESKTOP_BROWSER,
            'description': 'Latest Firefox on Linux'
        },
        'safari_mac': {
            'name': 'Safari (macOS)',
            'string': SAFARI_MAC,
            'category': UserAgentCategory.DESKTOP_BROWSER,
            'description': 'Latest Safari on macOS'
        },
        'edge_windows': {
            'name': 'Edge (Windows)',
            'string': EDGE_WINDOWS,
            'category': UserAgentCategory.DESKTOP_BROWSER,
            'description': 'Latest Edge on Windows 10/11'
        },
        'edge_mac': {
            'name': 'Edge (macOS)',
            'string': EDGE_MAC,
            'category': UserAgentCategory.DESKTOP_BROWSER,
            'description': 'Latest Edge on macOS'
        },
        'chrome_android': {
            'name': 'Chrome Mobile (Android)',
            'string': CHROME_ANDROID,
            'category': UserAgentCategory.MOBILE_BROWSER,
            'description': 'Chrome on Android smartphone'
        },
        'chrome_android_tablet': {
            'name': 'Chrome (Android Tablet)',
            'string': CHROME_ANDROID_TABLET,
            'category': UserAgentCategory.MOBILE_BROWSER,
            'description': 'Chrome on Android tablet'
        },
        'safari_iphone': {
            'name': 'Safari (iPhone)',
            'string': SAFARI_IPHONE,
            'category': UserAgentCategory.MOBILE_BROWSER,
            'description': 'Safari on iPhone'
        },
        'safari_ipad': {
            'name': 'Safari (iPad)',
            'string': SAFARI_IPAD,
            'category': UserAgentCategory.MOBILE_BROWSER,
            'description': 'Safari on iPad'
        },
        'firefox_android': {
            'name': 'Firefox Mobile (Android)',
            'string': FIREFOX_ANDROID,
            'category': UserAgentCategory.MOBILE_BROWSER,
            'description': 'Firefox on Android'
        },
        'googlebot': {
            'name': 'Googlebot',
            'string': GOOGLEBOT,
            'category': UserAgentCategory.BOT,
            'description': 'Google search crawler (desktop)'
        },
        'googlebot_smartphone': {
            'name': 'Googlebot Smartphone',
            'string': GOOGLEBOT_SMARTPHONE,
            'category': UserAgentCategory.BOT,
            'description': 'Google search crawler (mobile)'
        },
        'bingbot': {
            'name': 'Bingbot',
            'string': BINGBOT,
            'category': UserAgentCategory.BOT,
            'description': 'Bing search crawler'
        },
        'duckduckbot': {
            'name': 'DuckDuckBot',
            'string': DUCKDUCKBOT,
            'category': UserAgentCategory.BOT,
            'description': 'DuckDuckGo search crawler'
        },
        'scraper_default': {
            'name': 'scrape-api-docs (Default)',
            'string': SCRAPER_DEFAULT,
            'category': UserAgentCategory.DEFAULT,
            'description': 'Project default user agent'
        },
        'ie11_windows': {
            'name': 'Internet Explorer 11',
            'string': IE11_WINDOWS,
            'category': UserAgentCategory.DESKTOP_BROWSER,
            'description': 'Legacy IE11 on Windows (for testing)'
        }
    }

    @classmethod
    def get_all(cls) -> Dict[str, Dict[str, str]]:
        """
        Get all available user agents with metadata.
        
        Returns:
            Dictionary of user agent metadata keyed by identifier
        """
        return cls.METADATA.copy()

    @classmethod
    def get_by_category(cls, category: UserAgentCategory) -> Dict[str, Dict[str, str]]:
        """
        Get all user agents in a specific category.
        
        Args:
            category: The category to filter by
            
        Returns:
            Dictionary of user agent metadata for the category
        """
        return {
            key: value
            for key, value in cls.METADATA.items()
            if value['category'] == category
        }

    @classmethod
    def get_user_agent_string(cls, identifier: str) -> Optional[str]:
        """
        Get the user agent string for a given identifier.
        
        Args:
            identifier: The user agent identifier (e.g., 'chrome_windows')
            
        Returns:
            User agent string, or None if not found
        """
        metadata = cls.METADATA.get(identifier)
        return metadata['string'] if metadata else None

    @classmethod
    def list_identifiers(cls) -> List[str]:
        """
        Get a list of all available user agent identifiers.
        
        Returns:
            List of user agent identifiers
        """
        return list(cls.METADATA.keys())

    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        """
        Get a mapping of identifiers to display names.
        
        Returns:
            Dictionary mapping identifiers to display names
        """
        return {
            key: value['name']
            for key, value in cls.METADATA.items()
        }


def get_user_agent(identifier: str = 'chrome_windows', custom: Optional[str] = None) -> str:
    """
    Get a user agent string by identifier or custom string.
    
    Args:
        identifier: Predefined user agent identifier
        custom: Custom user agent string (overrides identifier if provided)
        
    Returns:
        User agent string
        
    Raises:
        ValueError: If identifier is not found and no custom string provided
    """
    if custom:
        return custom
    
    ua_string = UserAgents.get_user_agent_string(identifier)
    if ua_string is None:
        raise ValueError(
            f"Unknown user agent identifier: {identifier}. "
            f"Available: {UserAgents.list_identifiers()}"
        )
    
    return ua_string


def validate_user_agent(user_agent: str) -> bool:
    """
    Validate that a user agent string is reasonable.
    
    Args:
        user_agent: User agent string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not user_agent or not isinstance(user_agent, str):
        return False
    
    # Check minimum length
    if len(user_agent) < 3:
        return False
    
    # Check maximum length (reasonable upper bound)
    if len(user_agent) > 2000:
        return False
    
    # Check for suspicious characters (basic security check)
    suspicious_chars = ['\n', '\r', '\0']
    if any(char in user_agent for char in suspicious_chars):
        return False
    
    return True
