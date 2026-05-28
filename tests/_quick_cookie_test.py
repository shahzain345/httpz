import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import httpz

def main():
    with httpz.Client(cookies={"session": "abc-123", "auth": "token-xyz"}) as client:
        resp = client.get("https://httpbin.org/cookies")
        data = resp.json()
        print("Server received cookies:")
        print(json.dumps(data["cookies"], indent=2))
        print()
        session = data["cookies"].get("session")
        auth = data["cookies"].get("auth")
        print(f"session: {session} {'PASS' if session == 'abc-123' else 'FAIL'}")
        print(f"auth: {auth} {'PASS' if auth == 'token-xyz' else 'FAIL'}")

        client.cookies["second_cookie"] = "shahzain345"
        # request 2, check if cookies are being passed on to all requests.
        resp = client.get("https://httpbin.org/cookies")
        data = resp.json()
        print("Server received cookies:")
        print(json.dumps(data["cookies"], indent=2))
