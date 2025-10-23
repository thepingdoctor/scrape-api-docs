"""Core scraping functionality for documentation websites."""

import re
import requests
from bs4 import BeautifulSoup
import markdownify
from urllib.parse import urljoin, urlparse
from collections import deque


def get_all_site_links(base_url):
    """
    Crawls a website starting from the base URL to find all unique, internal pages.

    Args:
        base_url: The starting URL of the documentation site.

    Returns:
        A sorted list of unique absolute URLs belonging to the site.
    """
    to_visit = deque([base_url])
    visited = {base_url}
    all_links = {base_url}
    
    base_netloc = urlparse(base_url).netloc
    base_path = urlparse(base_url).path

    print(f"Crawling {base_url} to find all pages...")

    while to_visit:
        current_url = to_visit.popleft()

        try:
            session = requests.Session()
            response = session.get(current_url, timeout=10)
            response.raise_for_status()
            print(f"  - Visiting: {current_url}")

            soup = BeautifulSoup(response.text, 'html.parser')

            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                absolute_link = urljoin(current_url, href)

                parsed_link = urlparse(absolute_link)
                clean_link = parsed_link._replace(query="", fragment="").geturl()

                # Ensure the link is on the same domain and hasn't been visited/queued.
                # Also ensure it stays within the initial path (e.g., inside /docs/netbox/)
                if (urlparse(clean_link).netloc == base_netloc and
                        urlparse(clean_link).path.startswith(base_path) and
                        clean_link not in visited):
                    visited.add(clean_link)
                    all_links.add(clean_link)
                    to_visit.append(clean_link)

        except requests.exceptions.RequestException as e:
            print(f"    ! Error crawling {current_url}: {e}")
        except Exception as e:
            print(f"    ! An unexpected error occurred at {current_url}: {e}")

    print(f"Found {len(all_links)} unique pages.")
    return sorted(list(all_links))


def extract_main_content(html_content):
    """
    Extracts the main documentation content from a page.
    Targets the <main> element, which is common for modern doc sites.

    Args:
        html_content: The HTML content of a documentation page.

    Returns:
        The main content as an HTML string, or an empty string if not found.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    main_content = soup.find('main')
    if main_content:
        return str(main_content)
        
    main_content = soup.select_one('article, .main-content, #content')
    if main_content:
        return str(main_content)
        
    return ""


def convert_html_to_markdown(html_content):
    """
    Converts an HTML string to Markdown using the 'markdownify' library.

    Args:
        html_content: The HTML string to convert.

    Returns:
        The converted Markdown string.
    """
    return markdownify.markdownify(html_content, heading_style="ATX", bullets="*")


def generate_filename_from_url(base_url):
    """
    Generates a clean filename from a base URL.

    Args:
        base_url: The string of the base URL.

    Returns:
        A sanitized filename string.
    """
    path_part = urlparse(base_url).path.strip('/').replace('/', '_')
    domain_part = urlparse(base_url).netloc.replace(".", "_")
    # Handle case where path is empty
    if not path_part:
        return f"{domain_part}_documentation.md"
    return f"{domain_part}_{path_part}_documentation.md"


def scrape_site(base_url):
    """
    Scrapes an entire documentation site, combines all content, and saves it
    to a single Markdown file.

    Args:
        base_url: The base URL of the documentation site.
    """
    print(f"\nStarting scrape for documentation at: {base_url}")

    all_page_urls = get_all_site_links(base_url)
    full_documentation = ""

    main_title = " ".join(part.capitalize() for part in urlparse(base_url).path.strip('/').split('/'))
    full_documentation += f"# Documentation for {main_title or urlparse(base_url).netloc}\n"
    full_documentation += f"**Source:** {base_url}\n\n"

    for url in all_page_urls:
        print(f"  -> Processing {url}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            page_html = response.text

            soup = BeautifulSoup(page_html, 'html.parser')
            page_title = soup.title.string if soup.title else url
            page_title = re.sub(r'\|.*$| - .*$', '', page_title).strip()  # Clean the title more aggressively

            main_content_html = extract_main_content(page_html)
            
            if main_content_html:
                markdown_content = convert_html_to_markdown(main_content_html)
                
                full_documentation += f"## {page_title}\n\n"
                full_documentation += f"**Original Page:** `{url}`\n\n"
                full_documentation += markdown_content
                full_documentation += "\n\n---\n\n"
            else:
                print(f"     ! No main content found on {url}")

        except requests.exceptions.RequestException as e:
            print(f"     ! Failed to process {url}: {e}")

    output_filename = generate_filename_from_url(base_url)
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(full_documentation)

    print(f"\n✔ Success! All documentation has been saved to: {output_filename}")
