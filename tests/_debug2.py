import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stderr = sys.stdout  # merge stderr into stdout
import httpz

print("--- POST with custom headers ---", flush=True)
with httpz.Client() as client:
    resp = client.post(
        "https://httpbin.org/post",
        json={"test": "data"},
        headers={"X-Request-Id": "abc-123"},
    )
    data = resp.json()
    print(f"X-Request-Id: {data['headers'].get('X-Request-Id')}", flush=True)
