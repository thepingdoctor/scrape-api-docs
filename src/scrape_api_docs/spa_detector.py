"""
SPA (Single Page Application) detection for smart rendering decisions.

This module provides heuristics to automatically detect if a page requires
JavaScript rendering, enabling the hybrid renderer to make optimal choices.
"""

import logging
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Known SPA framework indicators
SPA_INDICATORS = [
    # React
    'data-react-root',
    'data-reactroot',
    'data-reactid',
    '__REACT_DEVTOOLS_GLOBAL_HOOK__',

    # Vue
    'data-v-',
    'v-app',
    'v-cloak',
    '__VUE__',

    # Angular
    'ng-app',
    'ng-version',
    'ng-controller',
    '_ngcontent-',

    # Next.js
    '__NEXT_DATA__',
    '__next',
    'next-route-announcer',

    # Nuxt
    '__NUXT__',
    '__nuxt',

    # Gatsby
    'data-gatsby',
    '___gatsby',

    # Svelte
    'data-svelte',
    '__svelte',

    # Docusaurus
    'data-theme',
    '__docusaurus',
]

# Meta generator values indicating SPA
SPA_GENERATORS = [
    'docusaurus',
    'vuepress',
    'gatsby',
    'hugo',
    'next.js',
    'nuxt',
    'gridsome',
    'sapper',
    'react-static',
]

# Root div patterns common in SPAs
ROOT_DIV_PATTERNS = [
    {'id': 'root'},
    {'id': 'app'},
    {'id': '__next'},
    {'id': '__nuxt'},
    {'id': 'gatsby-focus-wrapper'},
    {'class': 'app'},
]


class SPADetector:
    """
    Detects if a page requires JavaScript rendering.

    Uses multiple heuristics:
    1. SPA framework indicators in HTML
    2. Meta tags indicating static site generators
    3. Minimal content with root div patterns
    4. High script-to-content ratio
    5. Lazy-loaded content indicators
    """

    def __init__(
        self,
        content_threshold: int = 500,
        script_threshold: int = 5,
    ):
        """
        Initialize SPA detector.

        Args:
            content_threshold: Minimum text content length to consider page complete
            script_threshold: Minimum number of scripts to trigger detection
        """
        self.content_threshold = content_threshold
        self.script_threshold = script_threshold

    def needs_javascript_rendering(
        self,
        url: str,
        html: str,
        confidence_threshold: float = 0.5,
    ) -> bool:
        """
        Determine if JavaScript rendering is needed.

        Args:
            url: URL being analyzed (for logging)
            html: HTML content to analyze
            confidence_threshold: Confidence level (0-1) required to trigger JS rendering

        Returns:
            True if JavaScript rendering is recommended
        """
        confidence = self.calculate_spa_confidence(html)

        needs_js = confidence >= confidence_threshold

        logger.info(
            f"SPA detection for {url}: "
            f"confidence={confidence:.2f}, "
            f"needs_js={needs_js}"
        )

        return needs_js

    def calculate_spa_confidence(self, html: str) -> float:
        """
        Calculate confidence score (0-1) that page is an SPA.

        Returns:
            Confidence score from 0 (definitely static) to 1 (definitely SPA)
        """
        soup = BeautifulSoup(html, 'html.parser')

        score = 0.0
        max_score = 0.0

        # Check 1: SPA framework indicators (weight: 0.4)
        max_score += 0.4
        if self._has_spa_indicators(html, soup):
            score += 0.4
            logger.debug("Found SPA framework indicators")

        # Check 2: Meta generator tags (weight: 0.2)
        max_score += 0.2
        if self._has_spa_meta_tags(soup):
            score += 0.2
            logger.debug("Found SPA meta generator tag")

        # Check 3: Minimal content with root div (weight: 0.3)
        max_score += 0.3
        if self._has_minimal_content_with_root(soup):
            score += 0.3
            logger.debug("Found minimal content with root div pattern")

        # Check 4: High script-to-content ratio (weight: 0.1)
        max_score += 0.1
        if self._has_high_script_ratio(soup):
            score += 0.1
            logger.debug("Found high script-to-content ratio")

        confidence = score / max_score if max_score > 0 else 0.0
        return confidence

    def _has_spa_indicators(self, html: str, soup: BeautifulSoup) -> bool:
        """Check for SPA framework indicators."""
        # Check in raw HTML (faster for data attributes)
        for indicator in SPA_INDICATORS:
            if indicator in html:
                return True

        # Check in parsed soup (for complex attributes)
        for indicator in SPA_INDICATORS:
            if soup.find(attrs={indicator: True}):
                return True

        return False

    def _has_spa_meta_tags(self, soup: BeautifulSoup) -> bool:
        """Check for meta tags indicating SPA generators."""
        meta_generator = soup.find('meta', attrs={'name': 'generator'})

        if meta_generator:
            content = meta_generator.get('content', '').lower()
            for generator in SPA_GENERATORS:
                if generator.lower() in content:
                    return True

        return False

    def _has_minimal_content_with_root(self, soup: BeautifulSoup) -> bool:
        """Check for minimal content with typical SPA root div patterns."""
        for pattern in ROOT_DIV_PATTERNS:
            root = soup.find('div', pattern)
            if root:
                content = root.get_text(strip=True)
                if len(content) < self.content_threshold:
                    logger.debug(
                        f"Found root div {pattern} with minimal content "
                        f"({len(content)} chars)"
                    )
                    return True

        return False

    def _has_high_script_ratio(self, soup: BeautifulSoup) -> bool:
        """Check for high script-to-content ratio."""
        text_content = soup.get_text(strip=True)
        scripts = soup.find_all('script')

        # If lots of scripts but little text content, likely an SPA
        if len(scripts) > self.script_threshold and len(text_content) < self.content_threshold:
            logger.debug(
                f"High script ratio: {len(scripts)} scripts, "
                f"{len(text_content)} chars content"
            )
            return True

        return False

    def analyze_page_structure(self, html: str) -> dict:
        """
        Analyze page structure and return detailed metrics.

        Args:
            html: HTML content to analyze

        Returns:
            Dictionary with analysis metrics
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Count elements
        scripts = soup.find_all('script')
        links = soup.find_all('a')
        text_content = soup.get_text(strip=True)

        # Find framework indicators
        found_indicators = [
            indicator for indicator in SPA_INDICATORS
            if indicator in html or soup.find(attrs={indicator: True})
        ]

        # Check for root divs
        found_root_divs = [
            pattern for pattern in ROOT_DIV_PATTERNS
            if soup.find('div', pattern)
        ]

        # Meta tags
        meta_generator = soup.find('meta', attrs={'name': 'generator'})
        generator_content = meta_generator.get('content', '') if meta_generator else ''

        return {
            'total_scripts': len(scripts),
            'total_links': len(links),
            'text_content_length': len(text_content),
            'spa_indicators': found_indicators,
            'root_div_patterns': found_root_divs,
            'meta_generator': generator_content,
            'confidence_score': self.calculate_spa_confidence(html),
        }


# Convenience function
def detect_spa(html: str, url: str = '') -> bool:
    """
    Quick check if HTML requires JavaScript rendering.

    Args:
        html: HTML content
        url: URL (for logging)

    Returns:
        True if JavaScript rendering is recommended
    """
    detector = SPADetector()
    return detector.needs_javascript_rendering(url, html)
