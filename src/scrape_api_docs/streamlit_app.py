"""Streamlit web interface for the documentation scraper."""

import streamlit as st
import threading
import time
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
import os
from typing import List, Dict, Optional, Tuple
from scrape_api_docs.scraper import (
    get_all_site_links,
    extract_main_content,
    convert_html_to_markdown,
    generate_filename_from_url,
)
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
):
    """
    Scrape a documentation site with progress tracking.

    Args:
        state: The ScraperState object to update.
        base_url: The base URL to scrape.
        timeout: Request timeout in seconds.
        max_pages: Optional maximum number of pages to scrape.
        custom_filename: Optional custom output filename.
    """
    state.is_running = True
    state.start_time = datetime.now()
    state.status_message = "Starting scrape..."
    state.errors = []
    state.processed_urls = []

    try:
        # Step 1: Discover all pages
        state.status_message = "Discovering pages..."
        state.discovered_urls = get_all_site_links(base_url)

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

                    state.processed_urls.append(url)
                else:
                    state.errors.append({"url": url, "error": "No main content found"})

            except Exception as e:
                state.errors.append({"url": url, "error": str(e)})

            time.sleep(0.1)  # Small delay to allow UI updates

        # Step 4: Save the file
        if state.is_running:
            state.content = full_documentation
            output_filename = custom_filename or generate_filename_from_url(base_url)
            state.output_filename = output_filename

            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(full_documentation)

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

    # Handle start button click
    if start_button:
        is_valid, error_msg = validate_url(url)

        if not is_valid:
            st.error(f"❌ {error_msg}")
        else:
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

        # Download button
        if st.session_state.output_filename and state.content:
            st.divider()
            st.download_button(
                label="⬇️ Download Markdown File",
                data=state.content,
                file_name=st.session_state.output_filename,
                mime="text/markdown",
                use_container_width=True,
                type="primary",
            )


def render_sidebar():
    """Render the sidebar with additional information."""
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown(
            """
            This tool crawls documentation websites and converts them into 
            a single Markdown file.
            
            **Features:**
            - 🔍 Automatic page discovery
            - 📝 HTML to Markdown conversion
            - ⚡ Real-time progress tracking
            - 📊 Detailed error reporting
            - 💾 Downloadable output
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
