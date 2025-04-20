from .client import Session, Response, Browser, USING_AZURETLS, disable_fallback

# Utility functions
def get_session(ja3=None, browser=Browser.CHROME, proxy=None, ordered_headers=None):
    """
    Create a session with optional JA3 fingerprinting, proxy, and headers
    
    Args:
        ja3: Optional JA3 string to use for fingerprinting
        browser: Browser profile to emulate
        proxy: Optional proxy URL to use
        ordered_headers: Optional list of (name, value) tuples for ordered headers
        
    Returns:
        Session: Configured session object
    """
    session = Session()
    
    if ja3 and USING_AZURETLS:
        session.apply_ja3(ja3, browser)
    
    if proxy:
        session.set_proxy(proxy)
    
    if ordered_headers:
        session.set_ordered_headers(ordered_headers)
    
    return session

def create_with_ja3(ja3, browser=Browser.CHROME, proxy=None, ordered_headers=None):
    """
    Create a session with mandatory JA3 fingerprinting
    
    This function will raise an error if JA3 fingerprinting is not available.
    
    Args:
        ja3: JA3 string to use for fingerprinting
        browser: Browser profile to emulate
        proxy: Optional proxy URL to use
        ordered_headers: Optional list of (name, value) tuples for ordered headers
        
    Returns:
        Session: Configured session object
        
    Raises:
        RuntimeError: If JA3 fingerprinting is not available
    """
    if not USING_AZURETLS:
        raise RuntimeError("JA3 fingerprinting requires the azuretls library, which is not available")
    
    session = Session()
    session.apply_ja3(ja3, browser)
    
    if proxy:
        session.set_proxy(proxy)
    
    if ordered_headers:
        session.set_ordered_headers(ordered_headers)
    
    return session

# httpx-like interface for simple requests
def request(method, url, **kwargs):
    """Send an HTTP request with the given method and URL."""
    with Session() as session:
        return session.request(method, url, **kwargs)

def get(url, headers=None):
    """Send a GET request."""
    return request("GET", url, headers=headers)

def post(url, data="", headers=None):
    """Send a POST request."""
    return request("POST", url, data=data, headers=headers)

def put(url, data="", headers=None):
    """Send a PUT request."""
    return request("PUT", url, data=data, headers=headers)

def delete(url, headers=None):
    """Send a DELETE request."""
    return request("DELETE", url, headers=headers)

def head(url):
    """Send a HEAD request."""
    return request("HEAD", url)

def patch(url, data="", headers=None):
    """Send a PATCH request."""
    return request("PATCH", url, data=data, headers=headers)

__all__ = [
    'Session', 
    'Response', 
    'Browser',
    'USING_AZURETLS',
    'disable_fallback',
    'get_session',
    'create_with_ja3',
    'request',
    'get',
    'post',
    'put',
    'delete',
    'head',
    'patch'
]
__version__ = "0.1.0" 