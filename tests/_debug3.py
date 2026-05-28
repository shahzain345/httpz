import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpz._bridge import Bridge
from httpz.headers import Headers

# Create a bridge and session directly
bridge = Bridge()
session_id = bridge.create_session({})
print(f"Session ID: {session_id}")

# Build request data exactly as client.py does
headers_obj = Headers({"X-Request-Id": "abc-123", "Authorization": "Bearer token"})
req_data = {
    "method": "POST",
    "url": "https://httpbin.org/post",
    "headers": headers_obj.to_ordered_pairs(),
    "body": json.dumps({"test": "data"}),
    "content_type": "application/json",
}
print(f"Request JSON being sent to Go:")
print(json.dumps(req_data, indent=2))

# Make request
raw_response = bridge.request(session_id, req_data)
print(f"\nRaw response keys: {list(raw_response.keys())}")

# Decode body
import base64
body = json.loads(base64.b64decode(raw_response["body_base64"]))
print(f"\nServer received headers:")
print(json.dumps(body.get("headers", {}), indent=2))

bridge.close_session(session_id)

# Check if debug log was created
if os.path.exists("D:\\httpz\\go_debug.log"):
    print("\n--- Go Debug Log ---")
    with open("D:\\httpz\\go_debug.log") as f:
        print(f.read())
else:
    print("\n[No Go debug log found]")
