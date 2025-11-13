"""Streamlit web interface for the documentation scraper."""

import streamlit as st
import threading
import time
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from scrape_api_docs.scraper import (
    get_all_site_links,
    extract_main_content,
    convert_html_to_markdown,
    generate_filename_from_url,
)
from scrape_api_docs.user_agents import UserAgents, get_user_agent
from scrape_api_docs.config import Config
from scrape_api_docs.exporters.base import PageResult, ExportOptions
from scrape_api_docs.exporters.orchestrator import ExportOrchestrator
import requests
from bs4 import BeautifulSoup
import re


class ScraperState:
    """Manages the state of the scraping operation."""

    def __init__(self):
        self.is_running = False
        self.progress = 0
        self.total_pages = 0
        self.current_url = ""
        self.discovered_urls = []
        self.processed_urls = []
        self.errors = []
        self.content = ""
        self.start_time = None
        self.end_time = None
        self.status_message = "Ready to start scraping"
        self.output_filename = ""
        self.scraping_complete = False
        self.page_results: List[PageResult] = []
        self.export_results: Dict[str, Dict] = {}
        self.selected_formats: List[str] = ["markdown"]


def init_session_state():
    """Initialize Streamlit session state variables."""
    if "scraper_state" not in st.session_state:
        st.session_state.scraper_state = ScraperState()
    if "output_filename" not in st.session_state:
        st.session_state.output_filename = ""
    if "scraping_complete" not in st.session_state:
        st.session_state.scraping_complete = False


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate the input URL.

    Args:
        url: The URL to validate.

    Returns:
        A tuple of (is_valid, error_message).
    """
    if not url:
        return False, "URL cannot be empty"

    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False, "Invalid URL format. Must include scheme (http/https) and domain"
        if result.scheme not in ["http", "https"]:
            return False, "URL must use http or https protocol"
        return True, ""
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def scrape_with_progress(
    state: ScraperState,
    base_url: str,
    timeout: int = 10,
    max_pages: Optional[int] = None,
    custom_filename: Optional[str] = None,
    user_agent: Optional[str] = None,
    respect_robots: bool = True,
    enable_rate_limiting: bool = True,
    requests_per_second: float = 2.0,
    politeness_delay: float = 1.0,
    selected_formats: List[str] = None,
):
    """
    Scrape a documentation site with progress tracking.

    Args:
        state: The ScraperState object to update.
        base_url: The base URL to scrape.
        timeout: Request timeout in seconds.
        max_pages: Optional maximum number of pages to scrape.
        custom_filename: Optional custom output filename.
        user_agent: User agent string or identifier to use.
        respect_robots: Whether to respect robots.txt rules.
        enable_rate_limiting: Whether to enable rate limiting.
        requests_per_second: Number of requests per second.
        politeness_delay: Delay between requests in seconds.
    """
    state.is_running = True
    state.start_time = datetime.now()
    state.status_message = "Starting scrape..."
    state.errors = []
    state.processed_urls = []

    try:
        # Create custom config with user settings
        config = Config.load()
        config.set('scraper.timeout', timeout)
        config.set('robots.enabled', respect_robots)
        config.set('rate_limiting.enabled', enable_rate_limiting)
        config.set('rate_limiting.requests_per_second', requests_per_second)
        config.set('scraper.politeness_delay', politeness_delay)
        
        # Step 1: Discover all pages
        state.status_message = "Discovering pages..."
        state.discovered_urls = get_all_site_links(
            base_url, 
            user_agent=user_agent,
            config=config
        )

        if max_pages and len(state.discovered_urls) > max_pages:
            state.discovered_urls = state.discovered_urls[:max_pages]

        state.total_pages = len(state.discovered_urls)

        # Step 2: Build the documentation
        full_documentation = ""
        main_title = " ".join(
            part.capitalize() for part in urlparse(base_url).path.strip("/").split("/")
        )
        full_documentation += f"# Documentation for {main_title or urlparse(base_url).netloc}\n"
        full_documentation += f"**Source:** {base_url}\n"
        full_documentation += f"**Scraped on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # Step 3: Process each page
        for idx, url in enumerate(state.discovered_urls):
            if not state.is_running:  # Check if user stopped scraping
                state.status_message = "Scraping stopped by user"
                break

            state.current_url = url
            state.progress = ((idx + 1) / state.total_pages) * 100
            state.status_message = f"Processing page {idx + 1}/{state.total_pages}"

            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                page_html = response.text

                soup = BeautifulSoup(page_html, "html.parser")
                page_title = soup.title.string if soup.title else url
                page_title = re.sub(r"\|.*$| - .*$", "", page_title).strip()

                main_content_html = extract_main_content(page_html)

                if main_content_html:
                    markdown_content = convert_html_to_markdown(main_content_html)

                    full_documentation += f"## {page_title}\n\n"
                    full_documentation += f"**Original Page:** `{url}`\n\n"
                    full_documentation += markdown_content
                    full_documentation += "\n\n---\n\n"

                    # Store as PageResult for export
                    page_result = PageResult(
                        url=url,
                        title=page_title,
                        content=markdown_content,
                        format='markdown'
                    )
                    state.page_results.append(page_result)
                    state.processed_urls.append(url)
                else:
                    state.errors.append({"url": url, "error": "No main content found"})

            except Exception as e:
                state.errors.append({"url": url, "error": str(e)})

            time.sleep(0.1)  # Small delay to allow UI updates

        # Step 4: Save the file and generate exports
        if state.is_running:
            state.content = full_documentation
            
            # Generate base filename
            base_filename = custom_filename or generate_filename_from_url(base_url)
            if base_filename.endswith('.md'):
                base_filename = base_filename[:-3]
            
            # Ensure tmp directory exists
            tmp_dir = "tmp"
            os.makedirs(tmp_dir, exist_ok=True)
            
            # Save markdown file
            markdown_filepath = os.path.join(tmp_dir, f"{base_filename}.md")
            with open(markdown_filepath, "w", encoding="utf-8") as f:
                f.write(full_documentation)
            
            state.output_filename = f"{base_filename}.md"
            state.selected_formats = selected_formats or ["markdown"]
            
            # Generate additional export formats if requested
            if selected_formats and len(selected_formats) > 1 or (selected_formats and "markdown" not in selected_formats):
                state.status_message = "Generating export formats..."
                
                # Create export options
                export_options = ExportOptions(
                    title=main_title or urlparse(base_url).netloc,
                    source_url=base_url,
                    include_metadata=True,
                    include_toc=True
                )
                
                # Initialize orchestrator
                orchestrator = ExportOrchestrator()
                
                # Generate exports asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    export_results = loop.run_until_complete(
                        orchestrator.generate_exports(
                            pages=state.page_results,
                            base_url=base_url,
                            formats=[f for f in selected_formats if f != "markdown"],
                            output_dir=Path(tmp_dir),
                            options={fmt: export_options for fmt in selected_formats}
                        )
                    )
                    
                    # Store export results
                    for fmt, result in export_results.items():
                        if result.success:
                            state.export_results[fmt] = {
                                'path': str(result.output_path),
                                'size': result.size_bytes,
                                'success': True
                            }
                        else:
                            state.export_results[fmt] = {
                                'success': False,
                                'error': result.error
                            }
                            state.errors.append({
                                "url": "Export",
                                "error": f"{fmt.upper()} export failed: {result.error}"
                            })
                finally:
                    loop.close()

            state.status_message = "Scraping completed successfully!"
            state.scraping_complete = True
        else:
            state.status_message = "Scraping cancelled"

    except Exception as e:
        state.status_message = f"Error during scraping: {str(e)}"
        state.errors.append({"url": "N/A", "error": str(e)})

    finally:
        state.end_time = datetime.now()
        state.is_running = False
        state.progress = 100 if state.scraping_complete else state.progress


def render_header():
    """Render the application header."""
    st.title("📚 Documentation Scraper")
    st.markdown(
        """
        Crawl and scrape documentation websites, converting their content into a 
        single, consolidated Markdown file.
        """
    )
    st.divider()


def render_input_section():
    """Render the input section for URL and configuration."""
    st.header("🔧 Configuration")

    col1, col2 = st.columns([3, 1])

    with col1:
        url = st.text_input(
            "Documentation URL",
            placeholder="https://example.com/docs/",
            help="Enter the starting URL of the documentation to scrape",
            key="url_input",
        )

    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        start_button = st.button(
            "🚀 Start Scraping",
            type="primary",
            disabled=st.session_state.scraper_state.is_running,
            use_container_width=True,
        )

    # Advanced settings in expander
    with st.expander("⚙️ Advanced Settings"):
        col1, col2 = st.columns(2)

        with col1:
            timeout = st.number_input(
                "Request Timeout (seconds)",
                min_value=5,
                max_value=60,
                value=10,
                help="Timeout for each HTTP request",
            )

            max_pages = st.number_input(
                "Max Pages (0 = unlimited)",
                min_value=0,
                max_value=10000,
                value=0,
                help="Maximum number of pages to scrape. 0 means no limit.",
            )

        with col2:
            custom_filename = st.text_input(
                "Custom Output Filename (optional)",
                placeholder="my_documentation.md",
                help="Leave empty to auto-generate filename",
            )
        
        # Export Format Selection
        st.subheader("📦 Export Formats")
        
        # Check available formats
        orchestrator = ExportOrchestrator()
        available_formats = orchestrator.list_available_formats()
        
        format_options = {
            "markdown": "📝 Markdown - Clean, consolidated documentation",
            "pdf": "📄 PDF - Professional documents (requires WeasyPrint)",
            "epub": "📖 EPUB - E-book format for offline reading (requires ebooklib)",
            "html": "🌐 HTML - Standalone HTML with embedded styles",
            "json": "📊 JSON - Structured data for programmatic access"
        }
        
        # Build format list with availability indicators
        format_labels = []
        for fmt in ["markdown", "pdf", "epub", "html", "json"]:
            label = format_options[fmt]
            if fmt not in available_formats and fmt != "markdown":
                label += " ⚠️ (Not installed)"
            format_labels.append(label)
        
        selected_format_labels = st.multiselect(
            "Select export formats",
            options=format_labels,
            default=[format_labels[0]],  # Default to Markdown
            help="Choose one or more output formats. Markdown is always available."
        )
        
        # Map labels back to format names
        selected_formats = []
        for label in selected_format_labels:
            for fmt, desc in format_options.items():
                if label.startswith(desc.split(" -")[0]):
                    selected_formats.append(fmt)
                    break
        
        # Show warning if unavailable formats selected
        unavailable_selected = [f for f in selected_formats if f not in available_formats and f != "markdown"]
        if unavailable_selected:
            st.warning(
                f"⚠️ The following formats require additional dependencies: {', '.join(unavailable_selected)}. "
                "Install with: `pip install scrape-api-docs[all-formats]`",
                icon="⚠️"
            )
        
        # User Agent Selection
        st.subheader("🌐 User Agent")
        
        # Get all user agents organized by category
        all_user_agents = UserAgents.get_all()
        display_names = UserAgents.get_display_names()
        
        # Create options list with categories
        ua_options = ["Chrome (Windows) - Default"] + [
            display_names[key] for key in sorted(all_user_agents.keys())
        ] + ["Custom..."]
        
        user_agent_selection = st.selectbox(
            "Select User Agent",
            options=ua_options,
            index=0,
            help="Choose which browser/device to identify as when scraping"
        )
        
        # Handle custom user agent input
        custom_user_agent = None
        if user_agent_selection == "Custom...":
            custom_user_agent = st.text_input(
                "Custom User Agent String",
                placeholder="Mozilla/5.0 ...",
                help="Enter a custom user agent string"
            )
        
        # Robots.txt Compliance
        st.subheader("🤖 Robots.txt Compliance")
        
        respect_robots = st.checkbox(
            "Respect robots.txt rules",
            value=True,
            help="When enabled, the scraper will check and follow robots.txt directives"
        )
        
        if not respect_robots:
            st.warning(
                "⚠️ **Warning**: Only disable robots.txt compliance if you have explicit "
                "permission from the site owner. Ignoring robots.txt may violate the site's "
                "terms of service and could result in your IP being blocked.",
                icon="⚠️"
            )
        
        # Rate Limiting Controls
        st.subheader("🚦 Rate Limiting")
        
        enable_rate_limiting = st.checkbox(
            "Enable rate limiting",
            value=True,
            help="Limit the number of requests per second to avoid overwhelming the server"
        )
        
        if enable_rate_limiting:
            col_rate1, col_rate2 = st.columns(2)
            
            with col_rate1:
                requests_per_second = st.slider(
                    "Requests per second",
                    min_value=0.5,
                    max_value=10.0,
                    value=2.0,
                    step=0.5,
                    help="Number of requests allowed per second. Lower = more polite, slower scraping"
                )
            
            with col_rate2:
                politeness_delay = st.slider(
                    "Politeness delay (seconds)",
                    min_value=0.0,
                    max_value=5.0,
                    value=1.0,
                    step=0.1,
                    help="Additional delay between requests in seconds"
                )
        else:
            requests_per_second = 10.0  # High value when disabled
            politeness_delay = 0.0
            st.warning(
                "⚠️ **Warning**: Disabling rate limiting may cause the server to block your requests. "
                "Use with caution and only on sites you have permission to scrape.",
                icon="⚠️"
            )

    # Handle start button click
    if start_button:
        is_valid, error_msg = validate_url(url)

        if not is_valid:
            st.error(f"❌ {error_msg}")
        else:
            # Determine user agent to use
            selected_ua = None
            if user_agent_selection == "Custom...":
                if custom_user_agent:
                    selected_ua = custom_user_agent
            elif user_agent_selection != "Chrome (Windows) - Default":
                # Find the identifier for the selected display name
                for identifier, metadata in all_user_agents.items():
                    if metadata['name'] == user_agent_selection:
                        selected_ua = identifier
                        break
            
            st.session_state.scraping_complete = False
            st.session_state.scraper_state = ScraperState()

            # Start scraping in a background thread
            thread = threading.Thread(
                target=scrape_with_progress,
                args=(
                    st.session_state.scraper_state,
                    url,
                    timeout,
                    max_pages if max_pages > 0 else None,
                    custom_filename if custom_filename else None,
                    selected_ua,
                    respect_robots,
                    enable_rate_limiting,
                    requests_per_second,
                    politeness_delay,
                    selected_formats,
                ),
                daemon=True,
            )
            thread.start()
            st.rerun()

    # Stop button
    if st.session_state.scraper_state.is_running:
        if st.button("⏹️ Stop Scraping", type="secondary", use_container_width=False):
            st.session_state.scraper_state.is_running = False
            st.rerun()


def render_progress_section():
    """Render the progress and status section."""
    state = st.session_state.scraper_state

    if state.is_running or state.end_time:
        st.header("📊 Progress")

        # Progress bar
        progress_bar = st.progress(state.progress / 100 if state.total_pages > 0 else 0)

        # Status message
        st.info(f"**Status:** {state.status_message}")

        # Metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Pages", state.total_pages)

        with col2:
            st.metric("Processed", len(state.processed_urls))

        with col3:
            st.metric("Errors", len(state.errors))

        with col4:
            if state.start_time:
                elapsed = (
                    (state.end_time or datetime.now()) - state.start_time
                ).total_seconds()
                st.metric("Time Elapsed", f"{elapsed:.1f}s")

        # Current URL being processed
        if state.current_url and state.is_running:
            st.caption(f"Currently processing: `{state.current_url}`")

        # Auto-rerun while scraping
        if state.is_running:
            time.sleep(0.5)
            st.rerun()


def render_results_section():
    """Render the results section with tabs."""
    state = st.session_state.scraper_state

    if state.end_time or st.session_state.scraping_complete:
        st.header("📄 Results")

        tab1, tab2, tab3 = st.tabs(["📋 Overview", "👁️ Preview", "⚠️ Errors"])

        with tab1:
            st.subheader("Summary")

            summary_data = {
                "Metric": [
                    "Total Pages Discovered",
                    "Pages Successfully Processed",
                    "Pages with Errors",
                    "Output Filename",
                    "Scraping Duration",
                ],
                "Value": [
                    state.total_pages,
                    len(state.processed_urls),
                    len(state.errors),
                    st.session_state.output_filename,
                    f"{((state.end_time or datetime.now()) - state.start_time).total_seconds():.1f}s"
                    if state.start_time
                    else "N/A",
                ],
            }
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

            # Discovered URLs
            if state.discovered_urls:
                st.subheader("Discovered URLs")
                urls_df = pd.DataFrame(
                    {
                        "URL": state.discovered_urls,
                        "Status": [
                            "✅ Processed" if url in state.processed_urls else "❌ Failed"
                            for url in state.discovered_urls
                        ],
                    }
                )
                st.dataframe(urls_df, use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("Content Preview")
            if state.content:
                # Show first 5000 characters
                preview_content = state.content[:5000]
                if len(state.content) > 5000:
                    preview_content += "\n\n... (content truncated for preview)"

                st.markdown(preview_content)
            else:
                st.info("No content available yet")

        with tab3:
            st.subheader("Error Log")
            if state.errors:
                errors_df = pd.DataFrame(state.errors)
                st.dataframe(errors_df, use_container_width=True, hide_index=True)
            else:
                st.success("No errors encountered! 🎉")

        # Download buttons for all formats
        if st.session_state.output_filename and state.content:
            st.divider()
            st.subheader("📥 Download Files")
            
            # Format icons and MIME types
            format_info = {
                "markdown": {"icon": "📝", "mime": "text/markdown"},
                "pdf": {"icon": "📄", "mime": "application/pdf"},
                "epub": {"icon": "📖", "mime": "application/epub+zip"},
                "html": {"icon": "🌐", "mime": "text/html"},
                "json": {"icon": "📊", "mime": "application/json"}
            }
            
            # Show download buttons based on selected formats
            num_formats = len(state.selected_formats)
            cols = st.columns(min(num_formats, 3))
            
            for idx, fmt in enumerate(state.selected_formats):
                col_idx = idx % 3
                with cols[col_idx]:
                    if fmt == "markdown":
                        # Markdown is always available from state.content
                        st.download_button(
                            label=f"{format_info[fmt]['icon']} Download {fmt.upper()}",
                            data=state.content,
                            file_name=state.output_filename,
                            mime=format_info[fmt]['mime'],
                            use_container_width=True,
                            type="primary" if fmt == "markdown" else "secondary"
                        )
                    elif fmt in state.export_results:
                        result = state.export_results[fmt]
                        if result['success']:
                            # Read the exported file
                            try:
                                with open(result['path'], 'rb') as f:
                                    file_data = f.read()
                                
                                # Get filename from path
                                filename = os.path.basename(result['path'])
                                
                                # Show file size
                                size_mb = result['size'] / (1024 * 1024)
                                size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{result['size'] / 1024:.2f} KB"
                                
                                st.download_button(
                                    label=f"{format_info[fmt]['icon']} Download {fmt.upper()} ({size_str})",
                                    data=file_data,
                                    file_name=filename,
                                    mime=format_info[fmt]['mime'],
                                    use_container_width=True,
                                    type="secondary"
                                )
                            except Exception as e:
                                st.error(f"Error loading {fmt.upper()} file: {str(e)}")
                        else:
                            st.error(f"{fmt.upper()} export failed: {result.get('error', 'Unknown error')}")


def render_sidebar():
    """Render the sidebar with additional information."""
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown(
            """
            This tool crawls documentation websites and converts them into 
            multiple formats for easy reading and sharing.
            
            **Features:**
            - 🔍 Automatic page discovery
            - 📝 Multiple export formats (Markdown, PDF, EPUB, HTML, JSON)
            - ⚡ Real-time progress tracking
            - 📊 Detailed error reporting
            - 💾 Direct browser downloads
            """
        )

        st.divider()

        st.header("💡 Tips")
        st.markdown(
            """
            - Start with the base URL of the documentation
            - The scraper will find all pages within the same domain/path
            - Use the max pages setting to limit large sites
            - Check the errors tab if content is missing
            """
        )

        st.divider()

        st.header("🔗 Resources")
        st.markdown(
            """
            - [GitHub Repository](https://github.com/thepingdoctor/scrape-api-docs)
            - [Documentation](https://github.com/thepingdoctor/scrape-api-docs#readme)
            """
        )


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Documentation Scraper",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS
    st.markdown(
        """
        <style>
        .stProgress > div > div > div > div {
            background-color: #1f77b4;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    init_session_state()

    render_sidebar()
    render_header()
    render_input_section()
    render_progress_section()
    render_results_section()


if __name__ == "__main__":
    main()
