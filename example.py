#!/usr/bin/env python3
import json
import sys

# Import the httpz library
import httpz
from httpz import Session, Browser

def simple_example():
    """Simple example showing httpx-like interface"""
    print("== Simple Request Example ==")
    
    # Using top-level functions (like httpx)
    print("\nUsing top-level functions:")
    response = httpz.get("https://httpbin.org/get")
    print(f"Status code: {response.status_code}")
    print(f"Response: {json.dumps(response.json, indent=2)[:200]}...")
    
    # Using a session (like httpx.Client)
    print("\nUsing Session object:")
    with Session() as session:
        response = session.get("https://httpbin.org/get")
        print(f"Status code: {response.status_code}")
        print(f"Response: {json.dumps(response.json, indent=2)[:200]}...")

def headers_example():
    """Example demonstrating custom headers"""
    print("\n== Headers Example ==")
    
    # Set ordered headers (important for fingerprinting)
    ordered_headers = [
        ("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("accept-language", "en-US,en;q=0.9"),
        ("user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15")
    ]
    
    with Session() as session:
        session.set_ordered_headers(ordered_headers)
        response = session.get("https://httpbin.org/headers")
        print(f"Headers sent: {json.dumps(response.json.get('headers', {}), indent=2)}")

def ja3_example():
    """Example using JA3 fingerprinting"""
    print("\n== JA3 Fingerprinting Example ==")
    
    # Check if azuretls is available
    mode = "azuretls" if httpz.USING_AZURETLS else "fallback (requests)"
    print(f"Using {mode} mode")
    
    if not httpz.USING_AZURETLS:
        print("WARNING: azuretls is not available. JA3 fingerprinting will not work.")
        print("The example will continue using fallback mode with requests.")
        return
    
    # JA3 string to use
    ja3 = "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-21,29-23-24,0"
    
    # Create a session with the utility function
    session = httpz.get_session(ja3=ja3, browser=Browser.CHROME)
    
    # Set custom headers in a specific order 
    session.set_ordered_headers([
        ("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("accept-language", "en-US,en;q=0.9"),
        ("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")
    ])
    
    # Request JA3 check
    print("\nSending request to tls.peet.ws/api/all for JA3 analysis...")
    response = session.get("https://tls.peet.ws/api/all")
    
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        # Extract JA3 info
        ja3_info = response.json.get('tls', {}).get('ja3', None)
        if ja3_info:
            print(f"Server detected JA3: {ja3_info}")
            print(f"JA3 match: {ja3_info == ja3}")
    
    # Clean up
    session.close()

def cookies_example():
    """Example demonstrating cookie handling"""
    print("\n== Cookies Example ==")
    
    with Session() as session:
        # Set a cookie
        response = session.get("https://httpbin.org/cookies/set?cookie1=value1&cookie2=value2")
        
        # Show cookies received
        print("Cookies received:")
        for cookie in response.cookies:
            print(f"  {cookie['name']} = {cookie['value']}")
        
        # Make another request with the cookies
        response = session.get("https://httpbin.org/cookies")
        print(f"\nCookies sent in next request: {json.dumps(response.json, indent=2)}")

def methods_example():
    """Example demonstrating different HTTP methods"""
    print("\n== HTTP Methods Example ==")
    
    with Session() as session:
        # GET request
        response = session.get("https://httpbin.org/get?param=value")
        print(f"GET response status: {response.status_code}")
        
        # POST request with JSON
        data = json.dumps({"key": "value"})
        headers = {"Content-Type": "application/json"}
        response = session.post("https://httpbin.org/post", data=data, headers=headers)
        print(f"POST response status: {response.status_code}")
        
        # PUT request
        response = session.put("https://httpbin.org/put", data="test data")
        print(f"PUT response status: {response.status_code}")
        
        # DELETE request
        response = session.delete("https://httpbin.org/delete")
        print(f"DELETE response status: {response.status_code}")

if __name__ == "__main__":
    examples = {
        "simple": simple_example,
        "headers": headers_example,
        "ja3": ja3_example,
        "cookies": cookies_example,
        "methods": methods_example,
        "all": lambda: [simple_example(), headers_example(), ja3_example(), cookies_example(), methods_example()]
    }
    
    if len(sys.argv) > 1 and sys.argv[1] in examples:
        examples[sys.argv[1]]()
    else:
        print(f"Usage: {sys.argv[0]} [{'|'.join(examples.keys())}]")
        print("Running simple example...")
        simple_example() 