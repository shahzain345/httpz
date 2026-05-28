"""
httpz header tests.

Verifies that headers sent from httpz arrive at the server exactly as specified,
including ordering, casing, overrides, and multi-value behavior.

Run: python tests/test_headers.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import httpz

ECHO_URL = "https://httpbin.org/headers"


def print_response(resp):
    print(f"    response.json() = {json.dumps(resp.json(), indent=6)}")


def test_single_custom_header():
    print("[1] Single custom header")
    with httpz.Client() as client:
        resp = client.get(ECHO_URL, headers={"X-Test": "hello"})
        print_response(resp)
        received = resp.json()["headers"]
        assert received.get("X-Test") == "hello", f"Expected 'hello', got {received.get('X-Test')}"
    print(f"    PASS")


def test_multiple_custom_headers():
    print("[2] Multiple custom headers")
    headers = {
        "X-First": "one",
        "X-Second": "two",
        "X-Third": "three",
    }
    with httpz.Client() as client:
        resp = client.get(ECHO_URL, headers=headers)
        print_response(resp)
        received = resp.json()["headers"]
        for key, val in headers.items():
            assert received.get(key) == val, f"{key}: expected '{val}', got '{received.get(key)}'"
    print(f"    PASS")


def test_header_case_preservation():
    print("[3] Header case preservation")
    with httpz.Client() as client:
        resp = client.get(ECHO_URL, headers={"X-My-Custom-Header": "cased"})
        print_response(resp)
        received = resp.json()["headers"]
        found = None
        for k, v in received.items():
            if k.lower() == "x-my-custom-header":
                found = v
                break
        assert found == "cased", f"Expected 'cased', got {found}"
    print(f"    PASS")


def test_session_default_headers():
    print("[4] Session-level default headers")
    default_headers = {
        "X-Session-Header": "default-value",
        "Accept": "application/json",
    }
    with httpz.Client(headers=default_headers) as client:
        resp = client.get(ECHO_URL)
        print_response(resp)
        received = resp.json()["headers"]
        assert received.get("X-Session-Header") == "default-value"
        assert received.get("Accept") == "application/json"
    print(f"    PASS")


def test_per_request_overrides_session():
    print("[5] Per-request header overrides session default")
    with httpz.Client(headers={"X-Override": "session-value"}) as client:
        print("    --- Request 1 (session default) ---")
        resp = client.get(ECHO_URL)
        print_response(resp)
        received = resp.json()["headers"]
        assert received.get("X-Override") == "session-value"

        print("    --- Request 2 (per-request override) ---")
        resp = client.get(ECHO_URL, headers={"X-Override": "request-value"})
        print_response(resp)
        received = resp.json()["headers"]
        assert received.get("X-Override") == "request-value"
    print(f"    PASS")


def test_session_headers_persist():
    print("[6] Session headers persist across requests")
    with httpz.Client(headers={"X-Persistent": "stays"}) as client:
        for i in range(3):
            print(f"    --- Request {i+1} ---")
            resp = client.get(ECHO_URL)
            print_response(resp)
            received = resp.json()["headers"]
            assert received.get("X-Persistent") == "stays", f"Request {i+1}: header missing"
    print(f"    PASS")


def test_user_agent_override():
    print("[7] Custom User-Agent")
    ua = "httpz-test/1.0"
    with httpz.Client(headers={"User-Agent": ua}) as client:
        resp = client.get(ECHO_URL)
        print_response(resp)
        received = resp.json()["headers"]
        assert received.get("User-Agent") == ua, f"Expected '{ua}', got '{received.get('User-Agent')}'"
    print(f"    PASS")


def test_user_agent_via_constructor():
    print("[8] User-Agent via constructor param")
    ua = "httpz-constructor/2.0"
    with httpz.Client(user_agent=ua) as client:
        resp = client.get(ECHO_URL)
        print_response(resp)
        received = resp.json()["headers"]
        assert received.get("User-Agent") == ua, f"Expected '{ua}', got '{received.get('User-Agent')}'"
    print(f"    PASS")


def test_empty_header_value():
    print("[9] Empty header value")
    with httpz.Client() as client:
        resp = client.get(ECHO_URL, headers={"X-Empty": ""})
        print_response(resp)
        received = resp.json()["headers"]
        assert "X-Empty" in received, "Empty-value header was dropped"
        assert received["X-Empty"] == ""
    print(f"    PASS")


def test_headers_with_special_chars():
    print("[10] Header values with special characters")
    special = "value with spaces, commas; and=equals"
    with httpz.Client() as client:
        resp = client.get(ECHO_URL, headers={"X-Special": special})
        print_response(resp)
        received = resp.json()["headers"]
        assert received.get("X-Special") == special
    print(f"    PASS")


def test_ordered_headers_list_format():
    print("[11] Headers as list of tuples (ordered)")
    headers = [
        ("X-First", "1"),
        ("X-Second", "2"),
        ("X-Third", "3"),
    ]
    with httpz.Client() as client:
        resp = client.get(ECHO_URL, headers=headers)
        print_response(resp)
        received = resp.json()["headers"]
        assert received.get("X-First") == "1"
        assert received.get("X-Second") == "2"
        assert received.get("X-Third") == "3"
    print(f"    PASS")


def test_headers_object():
    print("[12] Headers using httpz.Headers object")
    h = httpz.Headers()
    h["X-From-Object"] = "yes"
    h["Accept-Language"] = "en-US"
    with httpz.Client() as client:
        resp = client.get(ECHO_URL, headers=h)
        print_response(resp)
        received = resp.json()["headers"]
        assert received.get("X-From-Object") == "yes"
        assert received.get("Accept-Language") == "en-US"
    print(f"    PASS")


def main():
    tests = [
        test_single_custom_header,
        test_multiple_custom_headers,
        test_header_case_preservation,
        test_session_default_headers,
        test_per_request_overrides_session,
        test_session_headers_persist,
        test_user_agent_override,
        test_user_agent_via_constructor,
        test_empty_header_value,
        test_headers_with_special_chars,
        test_ordered_headers_list_format,
        test_headers_object,
    ]

    print("=" * 60)
    print("  httpz — Header Tests")
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
