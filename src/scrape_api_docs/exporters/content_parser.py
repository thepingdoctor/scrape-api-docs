"""Content parser for extracting structured documentation elements."""

import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag, NavigableString
from urllib.parse import urljoin


class ContentParser:
    """Parse HTML/Markdown content into structured sections."""

    def __init__(self, base_url: str = ""):
        self.base_url = base_url

    def parse_content(self, html_content: str) -> Dict[str, Any]:
        """
        Parse HTML content into structured sections.
        
        Returns:
            Dict with sections, description, and metadata
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        self._clean_soup(soup)
        
        # Extract description from first paragraph
        description = self._extract_description(soup)
        
        # Build hierarchical section structure
        sections = self._build_sections(soup)
        
        # Extract links
        links = self._extract_links(soup)
        
        return {
            'description': description,
            'sections': sections,
            'links': links
        }

    def _clean_soup(self, soup: BeautifulSoup) -> None:
        """Remove unwanted elements from soup."""
        # Remove script and style tags
        for tag in soup(['script', 'style', 'noscript', 'iframe']):
            tag.decompose()
        
        # Remove common navigation/footer elements
        for selector in ['nav', 'footer', 'header', '.navigation', '.footer', '.header', '.sidebar', '.cookie-banner', '.advertisement']:
            for element in soup.select(selector):
                element.decompose()
        
        # Remove elements with display:none or hidden
        for element in soup.find_all(style=re.compile(r'display:\s*none')):
            element.decompose()
        
        for element in soup.find_all(class_=re.compile(r'hidden')):
            element.decompose()

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract description from first meaningful paragraph."""
        # Try to find first paragraph after first heading
        first_heading = soup.find(['h1', 'h2'])
        if first_heading:
            # Look for first paragraph after heading
            for sibling in first_heading.next_siblings:
                if isinstance(sibling, Tag) and sibling.name == 'p':
                    text = self._clean_text(sibling.get_text())
                    if len(text) > 20:  # Meaningful paragraph
                        return text[:500]  # Limit to 500 chars
        
        # Fallback: find any first meaningful paragraph
        for p in soup.find_all('p'):
            text = self._clean_text(p.get_text())
            if len(text) > 20:
                return text[:500]
        
        return ""

    def _build_sections(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Build hierarchical section structure from headings."""
        sections = []
        current_section = None
        section_id = 0
        
        # Find all elements
        elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'pre', 'table', 'blockquote'])
        
        for element in elements:
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(element.name[1])
                section_id += 1
                
                # Create new section
                new_section = {
                    'id': f'section_{section_id:03d}',
                    'heading': self._clean_text(element.get_text()),
                    'level': level,
                    'content': '',
                    'subsections': [],
                    'code_examples': [],
                    'tables': [],
                    'lists': []
                }
                
                # Determine where to place this section
                if level == 1:
                    sections.append(new_section)
                    current_section = new_section
                elif current_section:
                    # Add as subsection to current section
                    self._add_subsection(current_section, new_section, level)
                else:
                    sections.append(new_section)
                    current_section = new_section
            
            elif current_section:
                # Add content to current section
                self._add_content_to_section(current_section, element)
        
        return sections

    def _add_subsection(self, parent: Dict, new_section: Dict, level: int) -> None:
        """Add subsection to appropriate parent based on level."""
        parent_level = parent['level']
        
        if level == parent_level + 1:
            # Direct child
            parent['subsections'].append(new_section)
        elif parent['subsections']:
            # Try to add to last subsection
            self._add_subsection(parent['subsections'][-1], new_section, level)
        else:
            # Fallback: add as direct child
            parent['subsections'].append(new_section)

    def _add_content_to_section(self, section: Dict, element: Tag) -> None:
        """Add content element to section."""
        # If section has subsections, add to last subsection
        if section['subsections']:
            self._add_content_to_section(section['subsections'][-1], element)
            return
        
        if element.name == 'p':
            text = self._clean_text(element.get_text())
            if text:
                section['content'] += text + '\n\n'
        
        elif element.name in ['ul', 'ol']:
            list_data = self._extract_list(element)
            if list_data:
                section['lists'].append(list_data)
        
        elif element.name == 'pre':
            code_data = self._extract_code_block(element)
            if code_data:
                section['code_examples'].append(code_data)
        
        elif element.name == 'table':
            table_data = self._extract_table(element)
            if table_data:
                section['tables'].append(table_data)
        
        elif element.name == 'blockquote':
            text = self._clean_text(element.get_text())
            if text:
                section['content'] += f'> {text}\n\n'

    def _extract_list(self, list_element: Tag) -> Optional[Dict[str, Any]]:
        """Extract list data."""
        items = []
        for li in list_element.find_all('li', recursive=False):
            text = self._clean_text(li.get_text())
            if text:
                items.append(text)
        
        if not items:
            return None
        
        return {
            'type': 'ordered' if list_element.name == 'ol' else 'unordered',
            'items': items
        }

    def _extract_code_block(self, pre_element: Tag) -> Optional[Dict[str, Any]]:
        """Extract code block with language detection."""
        code = pre_element.find('code')
        code_text = code.get_text() if code else pre_element.get_text()
        
        # Detect language from class
        language = ''
        if code:
            classes = code.get('class', [])
            for cls in classes:
                if isinstance(cls, str):
                    if cls.startswith('language-') or cls.startswith('lang-'):
                        language = cls.split('-', 1)[1]
                        break
                    elif cls in ['python', 'javascript', 'java', 'ruby', 'php', 'go', 'rust', 'typescript', 'bash', 'shell', 'json', 'xml', 'yaml', 'sql']:
                        language = cls
                        break
        
        # Try to detect from content if no language found
        if not language:
            language = self._detect_language_from_content(code_text)
        
        # Extract title if present (sometimes in preceding element)
        title = ''
        if pre_element.previous_sibling:
            prev = pre_element.previous_sibling
            if isinstance(prev, Tag) and prev.name in ['p', 'div', 'span']:
                prev_text = self._clean_text(prev.get_text())
                if len(prev_text) < 100 and any(word in prev_text.lower() for word in ['example', 'code', 'snippet']):
                    title = prev_text
        
        return {
            'language': language,
            'code': code_text.strip(),
            'title': title,
            'line_count': len(code_text.splitlines())
        }

    def _detect_language_from_content(self, code: str) -> str:
        """Attempt to detect programming language from code content."""
        code_lower = code.lower()
        
        # Simple pattern matching
        if 'import ' in code or 'def ' in code or 'class ' in code_lower:
            return 'python'
        elif 'function' in code or 'const ' in code or 'let ' in code or '=>' in code:
            return 'javascript'
        elif 'curl ' in code or '#!/bin/bash' in code:
            return 'bash'
        elif '{' in code and '}' in code and '"' in code:
            return 'json'
        elif 'SELECT' in code.upper() or 'INSERT' in code.upper():
            return 'sql'
        
        return 'plaintext'

    def _extract_table(self, table_element: Tag) -> Optional[Dict[str, Any]]:
        """Extract table data."""
        # Extract caption
        caption = ''
        caption_elem = table_element.find('caption')
        if caption_elem:
            caption = self._clean_text(caption_elem.get_text())
        
        # Extract headers
        headers = []
        thead = table_element.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = [self._clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]
        
        # If no thead, try first row
        if not headers:
            first_row = table_element.find('tr')
            if first_row:
                headers = [self._clean_text(th.get_text()) for th in first_row.find_all('th')]
                if not headers:
                    # First row might be headers even if not in th tags
                    headers = [self._clean_text(td.get_text()) for td in first_row.find_all('td')]
        
        # Extract rows
        rows = []
        tbody = table_element.find('tbody') or table_element
        for tr in tbody.find_all('tr'):
            # Skip if this is the header row we already processed
            if tr.find('th') and not rows:
                continue
            
            cells = [self._clean_text(td.get_text()) for td in tr.find_all(['td', 'th'])]
            if cells:
                rows.append(cells)
        
        if not rows:
            return None
        
        return {
            'caption': caption,
            'headers': headers,
            'rows': rows
        }

    def _extract_links(self, soup: BeautifulSoup) -> Dict[str, List[Dict[str, str]]]:
        """Extract and categorize links."""
        internal_links = []
        external_links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = self._clean_text(link.get_text())
            
            if not text or href.startswith('#'):
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(self.base_url, href)
            
            link_data = {
                'text': text,
                'url': absolute_url
            }
            
            # Categorize as internal or external
            if self.base_url and absolute_url.startswith(self.base_url):
                internal_links.append(link_data)
            else:
                external_links.append(link_data)
        
        return {
            'internal': internal_links,
            'external': external_links
        }

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ''
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove zero-width spaces and other invisible characters
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for LLM context planning."""
        # Rough estimation: ~4 characters per token
        return len(text) // 4
