import json
from typing import Optional

from .client import Session, Browser, USING_AZURETLS

def get_session(proxy: Optional[str] = None, ja3: Optional[str] = None, browser: Browser = Browser.SAFARI) -> Session:
    """
    Create a session with a JA3 fingerprint.
    
    Args:
        proxy (str, optional): Proxy URL to use for the session
        ja3 (str, optional): JA3 fingerprint to use; if not provided, one will be fetched automatically
        browser (Browser, optional): Browser type to use with the JA3 fingerprint
        
    Returns:
        Session: A configured Session object
    """
    session = Session()
    
    try:
        # Handle JA3 configuration if azuretls is available
        if USING_AZURETLS:
            # If JA3 is provided, use it directly
            if ja3:
                try:
                    # Apply provided JA3 to the session
                    session.apply_ja3(ja3, browser)
                    print(f"Applied custom JA3 fingerprint: {ja3[:15]}...")
                except Exception as e:
                    print(f"Error applying custom JA3: {e}")
                    # Continue with ordered headers, etc.
            else:
                # No JA3 provided, try to fetch one
                try:
                    # Get JA3 fingerprint from the service
                    resp = session.get("http://cock.shahzain.me/get_ja3_joiner")
                    ja3_data = resp.json
                    ja3 = ja3_data.get("ja3")
                    
                    if ja3:
                        # Apply fetched JA3 to the session
                        try:
                            session.apply_ja3(ja3, browser)
                            print(f"Applied fetched JA3 fingerprint: {ja3[:15]}...")
                        except Exception as e:
                            print(f"Error applying fetched JA3: {e}")
                except Exception as e:
                    print(f"Error fetching JA3: {e}")
        
        # Set ordered headers
        ordered_headers = [
            ("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
            ("accept-language", "en-US,en;q=0.9"),
            ("priority", "u=0, i"),
            ("referer", "https://discord.com/"),
            ("sec-fetch-dest", "document"),
            ("sec-fetch-mode", "navigate"),
            ("sec-fetch-site", "same-origin"),
            ("user-agent", "Discord/75059 CFNetwork/3826.400.120 Darwin/24.3.0")
        ]
        session.set_ordered_headers(ordered_headers)
        
        # Set proxy if provided
        if proxy:
            session.set_proxy(proxy)
        
        # Send a request to discord.com to initialize the session
        try:
            session.get("https://discord.com")
        except Exception as e:
            print(f"Warning: Could not initialize session with discord.com: {e}")
        
    except Exception as e:
        print(f"Error initializing session: {e}")
    
    return session

def create_with_ja3(ja3: str, browser: Browser = Browser.SAFARI, proxy: Optional[str] = None) -> Session:
    """
    Create a session with a specific JA3 fingerprint.
    
    This is a convenience function that guarantees the use of the provided JA3 string,
    and will raise an error if azuretls is not available.
    
    Args:
        ja3 (str): JA3 fingerprint to use
        browser (Browser, optional): Browser type to use with the JA3 fingerprint
        proxy (str, optional): Proxy URL to use for the session
        
    Returns:
        Session: A configured Session object with the specified JA3 fingerprint
        
    Raises:
        RuntimeError: If azuretls is not available or JA3 application fails
    """
    if not USING_AZURETLS:
        raise RuntimeError("JA3 fingerprinting requires azuretls, which is not available")
        
    session = Session()
    
    # Apply the JA3 fingerprint
    session.apply_ja3(ja3, browser)
    
    # Set ordered headers
    ordered_headers = [
        ("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("accept-language", "en-US,en;q=0.9"),
        ("priority", "u=0, i"),
        ("user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15")
    ]
    session.set_ordered_headers(ordered_headers)
    
    # Set proxy if provided
    if proxy:
        session.set_proxy(proxy)
        
    return session 