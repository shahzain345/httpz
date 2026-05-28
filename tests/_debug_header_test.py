import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import httpz

# Test 1: See what the Python side sends to Go
print("=== Debug: What Python sends to Go ===")
from httpz.headers import Headers

# Simulate what client.request() does
default_headers = Headers()
req_headers = Headers({"X-Request-Id": "abc-123", "Authorization": "Bearer token"})
merged = default_headers.copy()
for k, v in req_headers.multi_items():
    merged[k] = v
ordered_pairs = merged.to_ordered_pairs()
print(f"ordered_pairs = {json.dumps(ordered_pairs)}")

# Test 2: Simple request without custom headers (baseline)
print("\n=== Test: GET without custom headers ===")
with httpz.Client() as client:
    resp = client.get("https://httpbin.org/get")
    data = resp.json()
    print(f"Headers received by server: {json.dumps(data['headers'], indent=2)}")

# Test 3: POST with custom headers
print("\n=== Test: POST with custom headers ===")
with httpz.Client() as client:
    resp = client.post(
        "https://httpbin.org/post",
        json={"test": "data"},
        headers={"X-Request-Id": "abc-123", "Authorization": "Bearer token"},
    )
    data = resp.json()
    print(f"Headers received by server: {json.dumps(data['headers'], indent=2)}")
    xrid = data["headers"].get("X-Request-Id") or data["headers"].get("x-request-id")
    auth = data["headers"].get("Authorization") or data["headers"].get("authorization")
    print(f"\nX-Request-Id: {xrid}")
    print(f"Authorization: {auth}")

# Test 4: GET with custom headers (no body/content-type complexity)
print("\n=== Test: GET with custom headers ===")
with httpz.Client() as client:
    resp = client.get(
        "https://httpbin.org/get",
        headers={"X-Custom-Test": "hello123"},
    )
    data = resp.json()
    print(f"Headers received by server: {json.dumps(data['headers'], indent=2)}")
    custom = data["headers"].get("X-Custom-Test") or data["headers"].get("x-custom-test")
    print(f"\nX-Custom-Test: {custom}")
