"""API endpoint detector for extracting structured API documentation."""

import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag


class APIDetector:
    """Detect and extract API endpoints and related information."""

    HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
    
    def __init__(self):
        self.endpoint_patterns = [
            # Match paths like /v1/messages, /api/users/{id}
            r'(/[a-zA-Z0-9_\-/{}:]+)',
            # Match complete URLs
            r'(https?://[^\s]+/[a-zA-Z0-9_\-/{}:]+)',
        ]

    def extract_api_endpoints(self, section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract API endpoints from a section.
        
        Returns:
            List of API endpoint definitions
        """
        endpoints = []
        
        # Check section heading for HTTP method
        heading = section.get('heading', '')
        method = self._extract_http_method(heading)
        
        # Look for endpoint in heading
        endpoint_path = self._extract_endpoint_path(heading)
        
        if method and endpoint_path:
            # Found endpoint in heading
            endpoint = self._build_endpoint(
                method=method,
                path=endpoint_path,
                section=section
            )
            if endpoint:
                endpoints.append(endpoint)
        else:
            # Search in content and code examples
            endpoints.extend(self._find_endpoints_in_content(section))
        
        # Recursively search subsections
        for subsection in section.get('subsections', []):
            endpoints.extend(self.extract_api_endpoints(subsection))
        
        return endpoints

    def _extract_http_method(self, text: str) -> Optional[str]:
        """Extract HTTP method from text."""
        text_upper = text.upper()
        for method in self.HTTP_METHODS:
            if method in text_upper:
                return method
        return None

    def _extract_endpoint_path(self, text: str) -> Optional[str]:
        """Extract API endpoint path from text."""
        for pattern in self.endpoint_patterns:
            match = re.search(pattern, text)
            if match:
                path = match.group(1)
                # Validate it looks like an API path
                if '/' in path and not path.endswith('.html'):
                    return path
        return None

    def _build_endpoint(self, method: str, path: str, section: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build complete endpoint definition."""
        endpoint = {
            'method': method,
            'path': path,
            'description': section.get('content', '').strip()[:500],  # First 500 chars
            'parameters': [],
            'request_example': None,
            'response_example': None,
            'response_codes': []
        }
        
        # Extract parameters from tables
        for table in section.get('tables', []):
            params = self._extract_parameters_from_table(table)
            endpoint['parameters'].extend(params)
        
        # Extract request/response examples from code blocks
        for code_block in section.get('code_examples', []):
            if not endpoint['request_example'] and self._looks_like_request(code_block):
                endpoint['request_example'] = code_block
            elif not endpoint['response_example'] and self._looks_like_response(code_block):
                endpoint['response_example'] = code_block
        
        # Extract response codes from tables or content
        endpoint['response_codes'] = self._extract_response_codes(section)
        
        return endpoint

    def _extract_parameters_from_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract API parameters from a table."""
        parameters = []
        headers = table.get('headers', [])
        
        # Check if this looks like a parameter table
        headers_lower = [h.lower() for h in headers]
        if not any(keyword in ' '.join(headers_lower) for keyword in ['parameter', 'param', 'field', 'name']):
            return parameters
        
        # Find column indices
        name_idx = self._find_column_index(headers_lower, ['name', 'parameter', 'param', 'field'])
        type_idx = self._find_column_index(headers_lower, ['type', 'data type', 'datatype'])
        required_idx = self._find_column_index(headers_lower, ['required', 'mandatory', 'optional'])
        desc_idx = self._find_column_index(headers_lower, ['description', 'desc', 'details'])
        
        # Extract parameters from rows
        for row in table.get('rows', []):
            if len(row) < 2:
                continue
            
            param = {}
            
            if name_idx is not None and name_idx < len(row):
                param['name'] = row[name_idx]
            
            if type_idx is not None and type_idx < len(row):
                param['type'] = row[type_idx]
            else:
                param['type'] = 'string'  # Default
            
            if required_idx is not None and required_idx < len(row):
                req_text = row[required_idx].lower()
                param['required'] = 'yes' in req_text or 'true' in req_text or 'required' in req_text
            else:
                param['required'] = False
            
            if desc_idx is not None and desc_idx < len(row):
                param['description'] = row[desc_idx]
            else:
                # Use first non-name, non-type column as description
                for i, cell in enumerate(row):
                    if i not in [name_idx, type_idx, required_idx] and cell:
                        param['description'] = cell
                        break
            
            if 'name' in param:
                parameters.append(param)
        
        return parameters

    def _find_column_index(self, headers: List[str], keywords: List[str]) -> Optional[int]:
        """Find column index by matching keywords."""
        for i, header in enumerate(headers):
            if any(keyword in header for keyword in keywords):
                return i
        return None

    def _looks_like_request(self, code_block: Dict[str, Any]) -> bool:
        """Check if code block looks like an API request."""
        code = code_block.get('code', '').lower()
        title = code_block.get('title', '').lower()
        
        # Check for request indicators
        request_indicators = [
            'request', 'curl', 'post', 'get', 'put', 'delete',
            'http', 'fetch', 'axios', 'requests.', 'HttpClient'
        ]
        
        return any(indicator in code or indicator in title for indicator in request_indicators)

    def _looks_like_response(self, code_block: Dict[str, Any]) -> bool:
        """Check if code block looks like an API response."""
        code = code_block.get('code', '')
        title = code_block.get('title', '').lower()
        language = code_block.get('language', '').lower()
        
        # Check for response indicators
        if 'response' in title:
            return True
        
        # JSON responses
        if language == 'json' and ('{' in code or '[' in code):
            # Check for common response fields
            response_fields = ['status', 'data', 'result', 'error', 'message', 'id']
            return any(f'"{field}"' in code for field in response_fields)
        
        return False

    def _extract_response_codes(self, section: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract HTTP response codes and their meanings."""
        response_codes = []
        
        # Look in tables for status codes
        for table in section.get('tables', []):
            headers_lower = [h.lower() for h in table.get('headers', [])]
            
            # Check if this is a status code table
            if any(keyword in ' '.join(headers_lower) for keyword in ['status', 'code', 'response']):
                code_idx = self._find_column_index(headers_lower, ['code', 'status'])
                desc_idx = self._find_column_index(headers_lower, ['description', 'meaning', 'message'])
                
                for row in table.get('rows', []):
                    if code_idx is not None and code_idx < len(row):
                        code = row[code_idx]
                        # Extract numeric code
                        code_match = re.search(r'\b([1-5]\d{2})\b', code)
                        if code_match:
                            response_code = {
                                'code': int(code_match.group(1)),
                                'description': row[desc_idx] if desc_idx is not None and desc_idx < len(row) else ''
                            }
                            response_codes.append(response_code)
        
        # Look in content for common status codes
        if not response_codes:
            content = section.get('content', '')
            common_codes = [
                (200, 'OK'), (201, 'Created'), (204, 'No Content'),
                (400, 'Bad Request'), (401, 'Unauthorized'), (403, 'Forbidden'),
                (404, 'Not Found'), (500, 'Internal Server Error')
            ]
            
            for code, default_desc in common_codes:
                if str(code) in content:
                    # Try to extract description from nearby text
                    pattern = rf'{code}\s*[-:]\s*([^.\n]+)'
                    match = re.search(pattern, content)
                    desc = match.group(1) if match else default_desc
                    
                    response_codes.append({
                        'code': code,
                        'description': desc
                    })
        
        return response_codes

    def _find_endpoints_in_content(self, section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find API endpoints mentioned in content or code examples."""
        endpoints = []
        
        # Search in code examples
        for code_block in section.get('code_examples', []):
            code = code_block.get('code', '')
            
            # Look for HTTP methods and paths in code
            for method in self.HTTP_METHODS:
                # Pattern: METHOD /path or METHOD("path") or method: "path"
                patterns = [
                    rf'\b{method}\s+([/\w\-{{}}]+)',
                    rf'{method}\s*\(\s*["\']([/\w\-{{}}]+)["\']',
                    rf'{method.lower()}\s*:\s*["\']([/\w\-{{}}]+)["\']',
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, code, re.IGNORECASE)
                    for match in matches:
                        path = match.group(1)
                        if '/' in path:
                            endpoint = {
                                'method': method,
                                'path': path,
                                'description': section.get('heading', ''),
                                'parameters': [],
                                'request_example': code_block,
                                'response_example': None,
                                'response_codes': []
                            }
                            endpoints.append(endpoint)
        
        return endpoints

    def categorize_endpoints(self, endpoints: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize endpoints by resource/topic."""
        categories = {}
        
        for endpoint in endpoints:
            # Extract resource from path (first segment after /)
            path = endpoint.get('path', '')
            match = re.match(r'/(?:v\d+/)?([^/]+)', path)
            
            if match:
                resource = match.group(1).replace('-', '_').replace('{', '').replace('}', '')
            else:
                resource = 'general'
            
            if resource not in categories:
                categories[resource] = []
            
            categories[resource].append(endpoint)
        
        return categories
