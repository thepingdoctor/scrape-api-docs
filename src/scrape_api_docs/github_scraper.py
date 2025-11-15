"""
GitHub Repository Documentation Scraper
========================================

This module provides functionality to scrape documentation from GitHub repositories
using the GitHub REST API. It supports:
- URL detection and parsing for various GitHub URL formats
- Fetching directory structure and file content via GitHub API
- Filtering for documentation files (.md, .rst, .txt, etc.)
- Converting relative links to absolute GitHub URLs
- Integration with existing scraper architecture

Features:
- No authentication required for public repositories
- Rate limiting awareness (60 requests/hour unauthenticated)
- Preserves directory structure in output
- Supports both single files and entire directories
- Compatible with existing config and logging systems

Usage:
    from scrape_api_docs.github_scraper import scrape_github_repo

    output_path = scrape_github_repo(
        url='https://github.com/owner/repo/tree/main/docs',
        output_dir='.',
        max_files=100
    )
"""

import re
import time
import requests
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse, urljoin
import base64

from .config import Config
from .logging_config import get_logger, PerformanceLogger
from .exceptions import (
    ValidationException,
    NetworkException,
    ContentParsingException,
    RateLimitException
)
from .security import SecurityValidator
from .user_agents import get_user_agent, UserAgents

logger = get_logger(__name__)


# Documentation file extensions to include
DOC_EXTENSIONS = {
    '.md', '.markdown',      # Markdown
    '.rst',                  # reStructuredText
    '.txt',                  # Plain text
    '.adoc', '.asciidoc',   # AsciiDoc
    '.textile',              # Textile
    '.org',                  # Org-mode
    '.rdoc',                 # RDoc
}


def is_github_url(url: str) -> bool:
    """
    Check if URL is a GitHub repository URL.

    Supports various GitHub URL formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo/tree/branch/path
    - https://github.com/owner/repo/blob/branch/file.md
    - git@github.com:owner/repo.git (SSH)

    Args:
        url: URL to check

    Returns:
        True if URL is a GitHub repository URL
    """
    if not url:
        return False

    # Handle SSH URLs
    if url.startswith('git@github.com:'):
        return True

    # Handle HTTPS URLs
    try:
        parsed = urlparse(url)
        return parsed.netloc in ('github.com', 'www.github.com')
    except Exception:
        return False


def parse_github_url(url: str) -> Dict[str, str]:
    """
    Parse GitHub URL into components (owner, repo, branch, path).

    Extracts structured information from various GitHub URL formats:
    - https://github.com/owner/repo -> {owner, repo, branch: 'main', path: ''}
    - https://github.com/owner/repo/tree/dev/docs -> {owner, repo, branch: 'dev', path: 'docs'}
    - https://github.com/owner/repo/blob/main/README.md -> {owner, repo, branch: 'main', path: 'README.md'}
    - git@github.com:owner/repo.git -> {owner, repo, branch: 'main', path: ''}

    Args:
        url: GitHub URL to parse

    Returns:
        Dictionary with keys: owner, repo, branch, path, is_file

    Raises:
        ValidationException: If URL is not a valid GitHub URL
    """
    if not is_github_url(url):
        raise ValidationException(
            "Not a valid GitHub URL",
            details={'url': url}
        )

    # Handle SSH URLs
    if url.startswith('git@github.com:'):
        # Format: git@github.com:owner/repo.git
        match = re.match(r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$', url)
        if match:
            owner, repo = match.groups()
            return {
                'owner': owner,
                'repo': repo,
                'branch': 'main',  # Default branch
                'path': '',
                'is_file': False
            }
        else:
            raise ValidationException(
                "Invalid GitHub SSH URL format",
                details={'url': url}
            )

    # Handle HTTPS URLs
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]

    if len(path_parts) < 2:
        raise ValidationException(
            "GitHub URL must include owner and repository",
            details={'url': url, 'path_parts': path_parts}
        )

    owner = path_parts[0]
    repo = path_parts[1]
    branch = 'main'  # Default
    path = ''
    is_file = False

    # Check for tree (directory) or blob (file) URLs
    if len(path_parts) > 2:
        url_type = path_parts[2]  # 'tree', 'blob', etc.

        if url_type in ('tree', 'blob'):
            is_file = (url_type == 'blob')

            if len(path_parts) > 3:
                branch = path_parts[3]

                # Remaining parts are the path
                if len(path_parts) > 4:
                    path = '/'.join(path_parts[4:])

    return {
        'owner': owner,
        'repo': repo,
        'branch': branch,
        'path': path,
        'is_file': is_file
    }


def get_repo_tree(
    owner: str,
    repo: str,
    branch: str = "main",
    path: str = "",
    config: Optional[Config] = None,
    session: Optional[requests.Session] = None
) -> List[Dict]:
    """
    Get repository directory tree using GitHub API.

    Fetches the directory structure of a repository or subdirectory
    using the GitHub REST API's git/trees endpoint with recursive mode.

    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        branch: Branch name (default: 'main')
        path: Path within repository (empty for root)
        config: Configuration instance (optional)
        session: Requests session (optional)

    Returns:
        List of file/directory objects with keys: path, type, size, url, sha

    Raises:
        NetworkException: If API request fails
        ValidationException: If repository not found or invalid
        RateLimitException: If rate limit exceeded
    """
    if config is None:
        config = Config.load()

    if session is None:
        session = requests.Session()
        ua_string = config.get('scraper.user_agent', UserAgents.CHROME_WINDOWS)
        session.headers.update({'User-Agent': ua_string})

    timeout = config.get('scraper.timeout', 10)

    # First, get the branch SHA
    try:
        branch_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}"
        logger.debug(f"Fetching branch ref: {branch_url}")

        response = session.get(branch_url, timeout=timeout)

        # Check rate limiting
        if response.status_code == 403:
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
            if rate_limit_remaining == '0':
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_seconds = max(0, reset_time - time.time())
                raise RateLimitException(
                    f"GitHub API rate limit exceeded. Resets in {wait_seconds:.0f}s",
                    retry_after=wait_seconds,
                    details={
                        'limit': response.headers.get('X-RateLimit-Limit'),
                        'reset_time': reset_time
                    }
                )

        if response.status_code == 404:
            # Try alternative branch names
            for alt_branch in ['master', 'develop']:
                if alt_branch != branch:
                    logger.info(f"Branch '{branch}' not found, trying '{alt_branch}'")
                    branch_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{alt_branch}"
                    response = session.get(branch_url, timeout=timeout)
                    if response.status_code == 200:
                        branch = alt_branch
                        break

            if response.status_code == 404:
                raise ValidationException(
                    f"Repository or branch not found: {owner}/{repo}/{branch}",
                    details={'owner': owner, 'repo': repo, 'branch': branch}
                )

        response.raise_for_status()
        branch_data = response.json()
        tree_sha = branch_data['object']['sha']

    except requests.exceptions.RequestException as e:
        raise NetworkException(
            f"Failed to fetch branch info: {e}",
            url=branch_url,
            details={'owner': owner, 'repo': repo, 'branch': branch}
        )

    # Now get the tree recursively
    try:
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree_sha}?recursive=1"
        logger.debug(f"Fetching repository tree: {tree_url}")

        response = session.get(tree_url, timeout=timeout)

        # Check rate limiting
        if response.status_code == 403:
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
            if rate_limit_remaining == '0':
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_seconds = max(0, reset_time - time.time())
                raise RateLimitException(
                    f"GitHub API rate limit exceeded. Resets in {wait_seconds:.0f}s",
                    retry_after=wait_seconds,
                    details={
                        'limit': response.headers.get('X-RateLimit-Limit'),
                        'reset_time': reset_time
                    }
                )

        response.raise_for_status()
        tree_data = response.json()

        # Filter tree based on path if specified
        tree_items = tree_data.get('tree', [])

        if path:
            # Filter items that start with the specified path
            tree_items = [
                item for item in tree_items
                if item['path'].startswith(path)
            ]

        logger.info(
            f"Retrieved {len(tree_items)} items from {owner}/{repo}/{branch}"
            f"{('/' + path) if path else ''}"
        )

        # Log rate limit status
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        if rate_limit_remaining:
            logger.debug(f"GitHub API rate limit remaining: {rate_limit_remaining}")

        return tree_items

    except requests.exceptions.RequestException as e:
        raise NetworkException(
            f"Failed to fetch repository tree: {e}",
            url=tree_url,
            details={'owner': owner, 'repo': repo, 'branch': branch}
        )


def get_file_content(
    owner: str,
    repo: str,
    branch: str,
    filepath: str,
    config: Optional[Config] = None,
    session: Optional[requests.Session] = None
) -> str:
    """
    Get raw file content from GitHub.

    Fetches the content of a single file from a GitHub repository using
    the GitHub API's contents endpoint.

    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name
        filepath: Path to file within repository
        config: Configuration instance (optional)
        session: Requests session (optional)

    Returns:
        File content as string

    Raises:
        NetworkException: If API request fails
        ContentParsingException: If content decoding fails
        RateLimitException: If rate limit exceeded
    """
    if config is None:
        config = Config.load()

    if session is None:
        session = requests.Session()
        ua_string = config.get('scraper.user_agent', UserAgents.CHROME_WINDOWS)
        session.headers.update({'User-Agent': ua_string})

    timeout = config.get('scraper.timeout', 10)

    try:
        # Use contents API endpoint
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}?ref={branch}"
        logger.debug(f"Fetching file content: {api_url}")

        response = session.get(api_url, timeout=timeout)

        # Check rate limiting
        if response.status_code == 403:
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
            if rate_limit_remaining == '0':
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_seconds = max(0, reset_time - time.time())
                raise RateLimitException(
                    f"GitHub API rate limit exceeded. Resets in {wait_seconds:.0f}s",
                    retry_after=wait_seconds,
                    details={
                        'limit': response.headers.get('X-RateLimit-Limit'),
                        'reset_time': reset_time
                    }
                )

        response.raise_for_status()
        content_data = response.json()

        # Decode base64 content
        if 'content' in content_data:
            content_base64 = content_data['content']
            try:
                content = base64.b64decode(content_base64).decode('utf-8', errors='ignore')
                return content
            except Exception as e:
                raise ContentParsingException(
                    f"Failed to decode file content: {e}",
                    details={'filepath': filepath, 'owner': owner, 'repo': repo}
                )
        else:
            raise ContentParsingException(
                "No content found in API response",
                details={'filepath': filepath, 'owner': owner, 'repo': repo}
            )

    except requests.exceptions.RequestException as e:
        raise NetworkException(
            f"Failed to fetch file content: {e}",
            url=api_url,
            details={'filepath': filepath, 'owner': owner, 'repo': repo}
        )


def convert_relative_links(
    content: str,
    owner: str,
    repo: str,
    branch: str,
    current_file_path: str
) -> str:
    """
    Convert relative links in markdown content to absolute GitHub URLs.

    Converts links like:
    - [Link](./other.md) -> [Link](https://github.com/owner/repo/blob/branch/other.md)
    - [Link](../parent/file.md) -> [Link](https://github.com/owner/repo/blob/branch/parent/file.md)
    - [Image](./images/pic.png) -> [Image](https://github.com/owner/repo/blob/branch/images/pic.png)

    Args:
        content: Markdown content
        owner: Repository owner
        repo: Repository name
        branch: Branch name
        current_file_path: Path of current file (for resolving relative paths)

    Returns:
        Content with converted links
    """
    # Get directory of current file
    current_dir = str(Path(current_file_path).parent)
    if current_dir == '.':
        current_dir = ''

    def replace_link(match):
        link_text = match.group(1)
        link_url = match.group(2)

        # Skip absolute URLs
        if link_url.startswith(('http://', 'https://', '#', 'mailto:')):
            return match.group(0)

        # Resolve relative path
        if current_dir:
            resolved_path = str(Path(current_dir) / link_url)
        else:
            resolved_path = link_url

        # Normalize path (remove ./ and ../)
        resolved_path = str(Path(resolved_path).as_posix())

        # Create absolute GitHub URL
        absolute_url = f"https://github.com/{owner}/{repo}/blob/{branch}/{resolved_path}"

        return f"[{link_text}]({absolute_url})"

    # Replace markdown links: [text](url)
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, content)

    return content


def scrape_github_repo(
    url: str,
    output_dir: str = '.',
    max_files: int = 100,
    config: Optional[Config] = None,
    progress_callback: Optional[callable] = None
) -> str:
    """
    Main function to scrape GitHub repository documentation.

    Downloads documentation files from a GitHub repository and combines
    them into a single Markdown file, similar to scrape_site().

    Features:
    - Automatically detects and parses GitHub URLs
    - Filters for documentation file types
    - Preserves directory structure in output
    - Converts relative links to absolute GitHub URLs
    - Respects rate limiting
    - Provides detailed logging

    Args:
        url: GitHub repository URL (various formats supported)
        output_dir: Output directory for documentation file
        max_files: Maximum number of files to process
        config: Configuration instance (optional)

    Returns:
        Path to the output markdown file

    Raises:
        ValidationException: If URL is invalid or repository not found
        NetworkException: If API requests fail
        RateLimitException: If rate limit exceeded

    Example:
        >>> output = scrape_github_repo(
        ...     'https://github.com/python/cpython/tree/main/Doc',
        ...     output_dir='./docs',
        ...     max_files=50
        ... )
        >>> print(f"Documentation saved to: {output}")
    """
    if config is None:
        config = Config.load()

    # Validate configuration
    config.validate()

    logger.info(f"Starting GitHub repository scrape: {url}")

    with PerformanceLogger(logger, "github_scrape", url=url):
        # Parse GitHub URL
        try:
            parsed = parse_github_url(url)
            owner = parsed['owner']
            repo = parsed['repo']
            branch = parsed['branch']
            base_path = parsed['path']
            is_file = parsed['is_file']

            logger.info(
                f"Parsed GitHub URL: {owner}/{repo} "
                f"(branch: {branch}, path: {base_path or 'root'})"
            )
        except ValidationException as e:
            logger.error(f"Invalid GitHub URL: {e}")
            raise

        # Initialize session
        session = requests.Session()
        ua_string = config.get('scraper.user_agent', UserAgents.CHROME_WINDOWS)
        session.headers.update({'User-Agent': ua_string})

        # Verify whether the path is actually a file or directory
        # by checking with the GitHub API (don't trust URL format alone)
        actual_is_file = False
        if base_path:
            try:
                # Try to get the path as a directory/file via contents API
                api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{base_path}?ref={branch}"
                timeout = config.get('scraper.timeout', 10)
                response = session.get(api_url, timeout=timeout)
                
                if response.status_code == 200:
                    content_data = response.json()
                    # If it's a file, response is a dict with 'type': 'file'
                    # If it's a directory, response is a list of items
                    if isinstance(content_data, dict) and content_data.get('type') == 'file':
                        actual_is_file = True
                        logger.info(f"Verified path is a file: {base_path}")
                    else:
                        logger.info(f"Verified path is a directory: {base_path}")
                else:
                    # If we can't verify, fall back to URL-based detection
                    logger.warning(f"Could not verify path type, using URL-based detection")
                    actual_is_file = is_file
            except Exception as e:
                logger.warning(f"Error verifying path type: {e}, using URL-based detection")
                actual_is_file = is_file
        else:
            # Root directory
            actual_is_file = False

        # Handle single file vs directory
        if actual_is_file:
            # Single file mode
            logger.info(f"Scraping single file: {base_path}")
            files_to_process = [{'path': base_path, 'type': 'blob'}]
        else:
            # Directory mode - get repository tree
            try:
                tree_items = get_repo_tree(owner, repo, branch, base_path, config, session)

                # Filter for documentation files
                files_to_process = [
                    item for item in tree_items
                    if item['type'] == 'blob' and
                    Path(item['path']).suffix.lower() in DOC_EXTENSIONS
                ]

                logger.info(
                    f"Found {len(files_to_process)} documentation files "
                    f"(filtered from {len(tree_items)} total items)"
                )

                # Limit to max_files
                if len(files_to_process) > max_files:
                    logger.warning(
                        f"Limiting to {max_files} files (found {len(files_to_process)})"
                    )
                    files_to_process = files_to_process[:max_files]

            except (NetworkException, ValidationException, RateLimitException) as e:
                logger.error(f"Failed to fetch repository tree: {e}")
                raise

        # Initialize documentation content
        full_documentation = ""
        repo_title = f"{owner}/{repo}"
        if base_path:
            repo_title += f"/{base_path}"

        full_documentation += f"# Documentation for {repo_title}\n"
        full_documentation += f"**Source:** {url}\n"
        full_documentation += f"**Branch:** {branch}\n"
        full_documentation += f"**Scraped:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"

        # Notify about total files discovered
        total_files = len(files_to_process)
        if progress_callback:
            progress_callback({
                'status': 'discovered',
                'total_files': total_files,
                'files_to_process': [item['path'] for item in files_to_process]
            })

        # Process each file
        files_processed = 0
        files_failed = 0

        for idx, file_item in enumerate(files_to_process):
            filepath = file_item['path']
            
            # Notify progress callback about current file
            if progress_callback:
                progress_callback({
                    'status': 'processing',
                    'current_file': filepath,
                    'current_index': idx + 1,
                    'total_files': total_files,
                    'files_processed': files_processed,
                    'files_failed': files_failed
                })

            try:
                logger.info(f"Processing: {filepath}")

                # Fetch file content
                content = get_file_content(owner, repo, branch, filepath, config, session)

                # Convert relative links to absolute
                content = convert_relative_links(content, owner, repo, branch, filepath)

                # Add to documentation
                file_title = Path(filepath).name
                github_url = f"https://github.com/{owner}/{repo}/blob/{branch}/{filepath}"

                full_documentation += f"## {file_title}\n\n"
                full_documentation += f"**Path:** `{filepath}`\n"
                full_documentation += f"**URL:** {github_url}\n\n"
                full_documentation += content
                full_documentation += "\n\n---\n\n"

                files_processed += 1
                
                # Notify success
                if progress_callback:
                    progress_callback({
                        'status': 'success',
                        'file': filepath,
                        'files_processed': files_processed
                    })

                # Be polite to GitHub API
                time.sleep(0.5)

            except (NetworkException, ContentParsingException) as e:
                logger.error(f"Failed to process {filepath}: {e}")
                files_failed += 1
                
                # Notify error
                if progress_callback:
                    progress_callback({
                        'status': 'error',
                        'file': filepath,
                        'error': str(e),
                        'files_failed': files_failed
                    })

            except RateLimitException as e:
                logger.warning(f"Rate limit hit, stopping: {e}")
                if progress_callback:
                    progress_callback({
                        'status': 'rate_limit',
                        'error': str(e)
                    })
                break

        # Generate output filename
        output_filename = f"{owner}_{repo}_{branch}"
        if base_path:
            safe_path = base_path.replace('/', '_')
            output_filename += f"_{safe_path}"
        output_filename += "_documentation.md"

        # Apply security sanitization
        if config.get('security.sanitize_filenames', True):
            output_filename = SecurityValidator.sanitize_filename(output_filename)

        output_path = Path(output_dir) / output_filename

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write documentation to file
        encoding = config.get('output.encoding', 'utf-8')
        with open(output_path, 'w', encoding=encoding) as f:
            f.write(full_documentation)

        logger.info(
            f"GitHub scrape complete: {files_processed} files processed, "
            f"{files_failed} failed. Saved to: {output_path}"
        )

        return str(output_path)
