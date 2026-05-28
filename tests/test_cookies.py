"""
httpz cookie tests.

Verifies that cookies are set, sent, persisted across requests,
and updated from responses correctly.

Run: python tests/test_cookies.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import httpz


def print_response(resp):
    print(f"    response.json() = {json.dumps(resp.json(), indent=6, ensure_ascii=False)}")


def test_set_cookie_from_response():
    print("[1] Server sets a cookie, client receives it")
    with httpz.Client() as client:
        resp = client.get("https://httpbin.org/cookies/set/testcookie/testvalue")
        print_response(resp)
        data = resp.json()
        assert data["cookies"].get("testcookie") == "testvalue"
    print(f"    PASS")


def test_cookies_sent_back():
    print("[2] Cookies are sent back to the server on subsequent requests")
    with httpz.Client() as client:
        client.get("https://httpbin.org/cookies/set/sid/abc123")
        resp = client.get("https://httpbin.org/cookies")
        print_response(resp)
        data = resp.json()
        assert data["cookies"].get("sid") == "abc123", f"Expected 'abc123', got {data['cookies'].get('sid')}"
    print(f"    PASS")


def test_multiple_cookies():
    print("[3] Multiple cookies set and sent")
    with httpz.Client() as client:
        client.get("https://httpbin.org/cookies/set/cookie1/value1")
        client.get("https://httpbin.org/cookies/set/cookie2/value2")
        client.get("https://httpbin.org/cookies/set/cookie3/value3")
        resp = client.get("https://httpbin.org/cookies")
        print_response(resp)
        data = resp.json()
        assert data["cookies"].get("cookie1") == "value1"
        assert data["cookies"].get("cookie2") == "value2"
        assert data["cookies"].get("cookie3") == "value3"
    print(f"    PASS")


def test_cookie_overwrite():
    print("[4] Cookie value gets overwritten by server")
    with httpz.Client() as client:
        client.get("https://httpbin.org/cookies/set/key/old")
        resp = client.get("https://httpbin.org/cookies")
        print(f"    Before overwrite:")
        print_response(resp)
        assert resp.json()["cookies"].get("key") == "old"

        client.get("https://httpbin.org/cookies/set/key/new")
        resp = client.get("https://httpbin.org/cookies")
        print(f"    After overwrite:")
        print_response(resp)
        assert resp.json()["cookies"].get("key") == "new"
    print(f"    PASS")


def test_cookie_delete():
    print("[5] Cookie deleted by server")
    with httpz.Client() as client:
        client.get("https://httpbin.org/cookies/set/deleteme/present")
        resp = client.get("https://httpbin.org/cookies")
        print(f"    Before delete:")
        print_response(resp)
        assert resp.json()["cookies"].get("deleteme") == "present"

        client.get("https://httpbin.org/cookies/delete?deleteme=")
        resp = client.get("https://httpbin.org/cookies")
        print(f"    After delete:")
        print_response(resp)
        assert "deleteme" not in resp.json()["cookies"]
    print(f"    PASS")


def test_cookies_isolated_between_clients():
    print("[6] Cookies are isolated between different clients")
    with httpz.Client() as client1:
        client1.get("https://httpbin.org/cookies/set/client1/yes")

        with httpz.Client() as client2:
            resp = client2.get("https://httpbin.org/cookies")
            print(f"    Client2 cookies (should be empty):")
            print_response(resp)
            data = resp.json()
            assert "client1" not in data["cookies"], "Cookie leaked between clients"

        resp = client1.get("https://httpbin.org/cookies")
        print(f"    Client1 cookies (should have client1=yes):")
        print_response(resp)
        assert resp.json()["cookies"].get("client1") == "yes"
    print(f"    PASS")


def test_cookies_persist_across_requests():
    print("[7] Cookies persist across many requests")
    with httpz.Client() as client:
        client.get("https://httpbin.org/cookies/set/persistent/keepme")
        for i in range(5):
            resp = client.get("https://httpbin.org/cookies")
            data = resp.json()
            assert data["cookies"].get("persistent") == "keepme", f"Request {i+1}: cookie missing"
        print(f"    Cookie present in all 5 requests:")
        print_response(resp)
    print(f"    PASS")


def test_cookie_with_special_values():
    print("[8] Cookie with special characters in value")
    with httpz.Client() as client:
        client.get("https://httpbin.org/cookies/set/special/hello%20world%21")
        resp = client.get("https://httpbin.org/cookies")
        print_response(resp)
        data = resp.json()
        assert "special" in data["cookies"]
        print(f"    special = {data['cookies']['special']}")
    print(f"    PASS")


def test_cookies_with_post():
    print("[9] Cookies sent with POST requests")
    with httpz.Client() as client:
        client.get("https://httpbin.org/cookies/set/auth/token123")
        resp = client.post("https://httpbin.org/post", json={"action": "test"})
        print_response(resp)
        # httpbin /post doesn't echo cookies in the same way, check via /cookies
        resp = client.get("https://httpbin.org/cookies")
        print(f"    Cookies after POST:")
        print_response(resp)
        assert resp.json()["cookies"].get("auth") == "token123"
    print(f"    PASS")


def test_initial_cookies_constructor():
    print("[10] Cookies passed via Client constructor")
    with httpz.Client(cookies={"preloaded": "fromcode"}) as client:
        print(f"    client.cookies = {dict(client.cookies)}")
        assert client.cookies.get("preloaded") == "fromcode"
    print(f"    PASS")


def main():
    tests = [
        test_set_cookie_from_response,
        test_cookies_sent_back,
        test_multiple_cookies,
        test_cookie_overwrite,
        test_cookie_delete,
        test_cookies_isolated_between_clients,
        test_cookies_persist_across_requests,
        test_cookie_with_special_values,
        test_cookies_with_post,
        test_initial_cookies_constructor,
    ]

    print("=" * 60)
    print("  httpz — Cookie Tests")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"    FAIL: {e}")
        print()

    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
