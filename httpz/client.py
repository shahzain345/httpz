import json
import os
import pathlib
import requests
import warnings
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

# Define browser types
class Browser(str, Enum):
    CHROME = "Chrome"
    SAFARI = "Safari"
    FIREFOX = "Firefox"
    OPERA = "Opera"
    IOS = "iOS"

# Configuration
ALLOW_FALLBACK = True  # Set to False to disable fallback mode

# Initialize variables
USING_AZURETLS = False
lib = None
ffi = None

# Try to load the shared library if available
try:
    import cffi
    
    # Initialize CFFI
    ffi = cffi.FFI()
    ffi.cdef("""
        int64_t NewSession();
        char* ApplyJA3(int64_t session, char* ja3, char* browser);
        char* SetProxy(int64_t session, char* proxy);
        char* SetOrderedHeaders(int64_t session, char* headers);
        char* DoRequest(int64_t session, char* method, char* url, char* headers, char* body);
        void CloseSession(int64_t session);
        void FreeString(char* str);
    """)
    
    # Load the shared library
    current_dir = pathlib.Path(__file__).parent.parent
    lib_path = os.path.join(current_dir, "libazuretls.so")
    try:
        lib = ffi.dlopen(lib_path)
        USING_AZURETLS = True
    except OSError as e:
        error_msg = f"Failed to load libazuretls.so: {e}."
        if ALLOW_FALLBACK:
            warnings.warn(f"{error_msg} Using fallback requests implementation.")
        else:
            raise ImportError(f"{error_msg} Fallback mode is disabled.")
except ImportError as e:
    error_msg = f"CFFI not installed or encountered error: {e}."
    if ALLOW_FALLBACK:
        warnings.warn(f"{error_msg} Using fallback requests implementation.")
    else:
        raise ImportError(f"{error_msg} Fallback mode is disabled.")

def disable_fallback():
    """
    Disable the fallback mode. After calling this function, attempts to use 
    httpz without azuretls will raise errors instead of using the requests fallback.
    
    Note: This function must be called before creating any Session objects.
    """
    global ALLOW_FALLBACK
    ALLOW_FALLBACK = False
    
    # If azuretls is not available, raise an error immediately
    if not USING_AZURETLS:
        raise ImportError("azuretls is not available and fallback mode is now disabled")

class Response:
    """HTTP Response object"""
    
    def __init__(self, status_code: int, headers: Dict[str, str], body: str, cookies: List[Dict[str, str]]):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.cookies = cookies
        self._json = None
    
    @property
    def json(self):
        """Parse response body as JSON"""
        if self._json is None:
            try:
                self._json = json.loads(self.body)
            except json.JSONDecodeError:
                self._json = {}
        return self._json
    
    @property
    def text(self):
        """Return response body as text"""
        return self.body
    
    def __repr__(self):
        return f"<Response [{self.status_code}]>"

class Session:
    """HTTP session using azuretls-client if available, otherwise using requests"""
    
    def __init__(self):
        """Initialize a new session"""
        self._azuretls_session = None
        self._fallback_session = None
        
        if USING_AZURETLS and lib is not None:
            session_id = lib.NewSession()
            if session_id == 0:
                raise RuntimeError("Failed to create azuretls session")
            self._azuretls_session = session_id
        else:
            if not ALLOW_FALLBACK:
                raise RuntimeError("azuretls is not available and fallback mode is disabled")
            self._fallback_session = requests.Session()
            self._ordered_headers = []
    
    def apply_ja3(self, ja3: str, browser: Union[str, Browser] = Browser.CHROME) -> None:
        """Apply JA3 fingerprint to the session"""
        if not USING_AZURETLS or lib is None or ffi is None:
            if ALLOW_FALLBACK:
                warnings.warn("JA3 fingerprinting not available in fallback mode")
                return
            else:
                raise RuntimeError("JA3 fingerprinting requires azuretls, which is not available")
            
        if isinstance(browser, Browser):
            browser_str = browser.value
        else:
            browser_str = browser
            
        ja3_c = ffi.new("char[]", ja3.encode())
        browser_c = ffi.new("char[]", browser_str.encode())
        
        result = lib.ApplyJA3(self._azuretls_session, ja3_c, browser_c)
        if result:
            error = ffi.string(result).decode()
            lib.FreeString(result)  # Free the C string
            if error:
                raise RuntimeError(f"Failed to apply JA3: {error}")
    
    def set_proxy(self, proxy: str) -> None:
        """Set proxy for the session"""
        if USING_AZURETLS and lib is not None and ffi is not None and self._azuretls_session is not None:
            proxy_c = ffi.new("char[]", proxy.encode())
            result = lib.SetProxy(self._azuretls_session, proxy_c)
            if result:
                error = ffi.string(result).decode()
                lib.FreeString(result)  # Free the C string
                if error:
                    raise RuntimeError(f"Failed to set proxy: {error}")
        else:
            if self._fallback_session is None:
                raise RuntimeError("No active session available")
            proxies = {
                "http": proxy,
                "https": proxy
            }
            self._fallback_session.proxies.update(proxies)
    
    def set_ordered_headers(self, headers: List[Tuple[str, str]]) -> None:
        """Set ordered headers for the session"""
        if USING_AZURETLS and lib is not None and ffi is not None and self._azuretls_session is not None:
            headers_list = [[k, v] for k, v in headers]
            headers_json = json.dumps(headers_list)
            headers_c = ffi.new("char[]", headers_json.encode())
            
            result = lib.SetOrderedHeaders(self._azuretls_session, headers_c)
            if result:
                error = ffi.string(result).decode()
                lib.FreeString(result)  # Free the C string
                if error:
                    raise RuntimeError(f"Failed to set ordered headers: {error}")
        else:
            if self._fallback_session is None:
                raise RuntimeError("No active session available")
            # Store ordered headers for later use
            self._ordered_headers = headers
            
            # Also update the session headers
            for key, value in headers:
                self._fallback_session.headers[key] = value
    
    def request(self, method: str, url: str, headers: Optional[Dict[str, str]] = None, 
                data: Optional[str] = None) -> Response:
        """Make an HTTP request"""
        if USING_AZURETLS and lib is not None and ffi is not None and self._azuretls_session is not None:
            # Use azuretls implementation
            method_c = ffi.new("char[]", method.upper().encode())
            url_c = ffi.new("char[]", url.encode())
            
            headers_json = "{}"
            if headers:
                headers_json = json.dumps(headers)
            headers_c = ffi.new("char[]", headers_json.encode())
            
            body = "" if data is None else data
            body_c = ffi.new("char[]", body.encode())
            
            result_c = lib.DoRequest(self._azuretls_session, method_c, url_c, headers_c, body_c)
            result_str = ffi.string(result_c).decode()
            lib.FreeString(result_c)  # Free the C string
            
            try:
                result = json.loads(result_str)
                if "error" in result:
                    raise RuntimeError(f"Request failed: {result['error']}")
                    
                return Response(
                    status_code=result.get("status_code", 0),
                    headers=result.get("headers", {}),
                    body=result.get("body", ""),
                    cookies=result.get("cookies", [])
                )
            except json.JSONDecodeError:
                raise RuntimeError(f"Failed to parse response: {result_str}")
        else:
            # Use requests fallback implementation
            if self._fallback_session is None:
                raise RuntimeError("No active session available")
                
            req_headers = {}
            if headers:
                req_headers.update(headers)
                
            resp = self._fallback_session.request(
                method=method.upper(),
                url=url,
                headers=req_headers,
                data=data
            )
            
            # Convert cookies to list format
            cookies_list = []
            for cookie in resp.cookies:
                cookies_list.append({
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path
                })
            
            return Response(
                status_code=resp.status_code,
                headers=dict(resp.headers),
                body=resp.text,
                cookies=cookies_list
            )
    
    def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Response:
        """Make a GET request"""
        return self.request("GET", url, headers)
    
    def post(self, url: str, data: str = "", headers: Optional[Dict[str, str]] = None) -> Response:
        """Make a POST request"""
        return self.request("POST", url, headers, data)
    
    def put(self, url: str, data: str = "", headers: Optional[Dict[str, str]] = None) -> Response:
        """Make a PUT request"""
        return self.request("PUT", url, headers, data)
    
    def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> Response:
        """Make a DELETE request"""
        return self.request("DELETE", url, headers)
    
    def head(self, url: str) -> Response:
        """Make a HEAD request"""
        return self.request("HEAD", url)
    
    def patch(self, url: str, data: str = "", headers: Optional[Dict[str, str]] = None) -> Response:
        """Make a PATCH request"""
        return self.request("PATCH", url, headers, data)
    
    def close(self):
        """Close the session"""
        if USING_AZURETLS and lib is not None and self._azuretls_session:
            lib.CloseSession(self._azuretls_session)
            self._azuretls_session = None
        elif self._fallback_session:
            self._fallback_session.close()
    
    def __del__(self):
        """Cleanup when object is garbage collected"""
        self.close()
    
    def __enter__(self):
        """Context manager enter"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close() 