# httpz

A Python HTTP client that wraps around the [azuretls-client](https://github.com/Noooste/azuretls-client) Go package, providing easy-to-use JA3 fingerprinting capabilities with an API similar to httpx.

## Features

- **JA3 Fingerprinting**: Easily modify the TLS fingerprint of your HTTP requests
- **Browser Emulation**: Set a browser profile to match specific browser behavior
- **Ordered Headers**: Control the exact order of HTTP headers for better browser emulation
- **Fallback Mode**: Gracefully falls back to the `requests` library when the native library isn't available
- **httpx-like API**: Familiar interface for users of the popular httpx library

## Installation

```bash
pip install httpz-ja3
```

## Quick Start

```python
from httpz import Session

# Create a session
session = Session()

# Make a request
response = session.get("https://httpbin.org/get")
print(f"Status code: {response.status_code}")
print(response.json)
```

## JA3 Fingerprinting

```python
from httpz import Session, Browser

# Create a session
session = Session()

# Apply a specific JA3 fingerprint
ja3 = "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-21,29-23-24,0"
session.apply_ja3(ja3, browser=Browser.CHROME)

# Set custom headers in a specific order (important for fingerprinting)
session.set_ordered_headers([
    ("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
    ("accept-language", "en-US,en;q=0.9"),
    ("user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15")
])

# Make request
response = session.get("https://tls.peet.ws/api/all")

# Check the detected JA3 fingerprint
if response.status_code == 200:
    ja3_info = response.json.get('tls', {}).get('ja3', 'unknown')
    print(f"Server detected JA3: {ja3_info}")
```

## Convenience Functions

```python
from httpz import get_session, create_with_ja3, Browser

# Quick session creation with JA3
session = get_session(
    ja3="771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-21,29-23-24,0", 
    browser=Browser.SAFARI
)

# Ensure JA3 is applied (will raise error if azuretls not available)
session = create_with_ja3(
    ja3="771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-21,29-23-24,0", 
    browser=Browser.CHROME
)
```

## Cookie Handling

```python
from httpz import Session

session = Session()
response = session.get("https://httpbin.org/cookies/set?cookie1=value1")

# Access cookies
for cookie in response.cookies:
    print(f"Cookie: {cookie['name']} = {cookie['value']}")

# Make another request with the cookies
response = session.get("https://httpbin.org/cookies")
print(response.json)
```

## Context Manager Support

```python
from httpz import Session

with Session() as session:
    response = session.get("https://httpbin.org/get")
    print(response.json)
    # Session automatically closed when exiting the context
```

## httpx-like Interface

If you're familiar with httpx, you'll find httpz very similar to use:

```python
# httpx
import httpx
with httpx.Client() as client:
    response = client.get("https://httpbin.org/get")
    print(response.json())

# httpz
import httpz
with httpz.Session() as session:
    response = session.get("https://httpbin.org/get")
    print(response.json)
```

## Building from Source

If you want to build the library from source:

```bash
git clone https://github.com/username/httpz
cd httpz
make
python -m pip install -e .
```

## License

MIT License 
