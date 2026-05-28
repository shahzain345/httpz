"""
httpz POST data tests.

Verifies that JSON bodies, form-encoded data, raw bytes, and string bodies
are sent correctly and arrive at the server intact.

Run: python tests/test_post_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import httpz

POST_URL = "https://httpbin.org/post"


def print_response(resp):
    print(f"    response.json() = {json.dumps(resp.json(), indent=6, ensure_ascii=False)}")


def test_json_simple():
    print("[1] POST JSON — simple object")
    payload = {"name": "httpz", "version": "0.1.0"}
    with httpz.Client() as client:
        resp = client.post(POST_URL, json=payload)
        print_response(resp)
        data = resp.json()
        assert data["json"] == payload, f"Expected {payload}, got {data['json']}"
        ct = data["headers"].get("Content-Type", "")
        assert "application/json" in ct, f"Content-Type wrong: {ct}"
    print(f"    PASS")


def test_json_nested():
    print("[2] POST JSON — nested object")
    payload = {
        "user": {
            "name": "test",
            "settings": {"theme": "dark", "notifications": True},
        },
        "tags": ["python", "go", "tls"],
        "count": 42,
    }
    with httpz.Client() as client:
        resp = client.post(POST_URL, json=payload)
        print_response(resp)
        data = resp.json()
        assert data["json"] == payload
    print(f"    PASS")


def test_json_types():
    print("[3] POST JSON — various types")
    payload = {
        "string": "hello",
        "integer": 123,
        "float": 3.14,
        "bool_true": True,
        "bool_false": False,
        "null": None,
        "array": [1, "two", 3.0],
    }
    with httpz.Client() as client:
        resp = client.post(POST_URL, json=payload)
        print_response(resp)
        data = resp.json()
        assert data["json"]["string"] == "hello"
        assert data["json"]["integer"] == 123
        assert data["json"]["float"] == 3.14
        assert data["json"]["bool_true"] is True
        assert data["json"]["bool_false"] is False
        assert data["json"]["null"] is None
        assert data["json"]["array"] == [1, "two", 3.0]
    print(f"    PASS")


def test_json_unicode():
    print("[4] POST JSON — unicode characters")
    payload = {"emoji": "Hello World", "chinese": "你好世界", "arabic": "مرحبا"}
    with httpz.Client() as client:
        resp = client.post(POST_URL, json=payload)
        print_response(resp)
        data = resp.json()
        assert data["json"] == payload
    print(f"    PASS")


def test_json_empty():
    print("[5] POST JSON — empty object")
    with httpz.Client() as client:
        resp = client.post(POST_URL, json={})
        print_response(resp)
        data = resp.json()
        assert data["json"] == {}
    print(f"    PASS")


def test_form_data_simple():
    print("[6] POST form data — simple")
    payload = {"username": "admin", "password": "secret123"}
    with httpz.Client() as client:
        resp = client.post(POST_URL, data=payload)
        print_response(resp)
        data = resp.json()
        assert data["form"] == payload, f"Expected {payload}, got {data['form']}"
        ct = data["headers"].get("Content-Type", "")
        assert "application/x-www-form-urlencoded" in ct
    print(f"    PASS")


def test_form_data_special_chars():
    print("[7] POST form data — special characters")
    payload = {"query": "hello world&more=yes", "path": "/a/b?c=d"}
    with httpz.Client() as client:
        resp = client.post(POST_URL, data=payload)
        print_response(resp)
        data = resp.json()
        assert data["form"]["query"] == "hello world&more=yes"
        assert data["form"]["path"] == "/a/b?c=d"
    print(f"    PASS")


def test_form_data_empty_value():
    print("[8] POST form data — empty value")
    payload = {"key": "", "other": "present"}
    with httpz.Client() as client:
        resp = client.post(POST_URL, data=payload)
        print_response(resp)
        data = resp.json()
        assert data["form"]["key"] == ""
        assert data["form"]["other"] == "present"
    print(f"    PASS")


def test_raw_string_body():
    print("[9] POST raw string body")
    body = "this is raw text content"
    with httpz.Client() as client:
        resp = client.post(POST_URL, data=body)
        print_response(resp)
        data = resp.json()
        assert data["data"] == body
    print(f"    PASS")


def test_raw_bytes_body():
    print("[10] POST raw bytes body (via content=)")
    body = b"binary content \x00\x01\x02\xff"
    with httpz.Client() as client:
        resp = client.post(POST_URL, content=body)
        print_response(resp)
        data = resp.json()
        assert len(data["data"]) > 0, "No data received"
    print(f"    PASS")


def test_bytes_via_data():
    print("[11] POST bytes via data= parameter")
    body = b"some bytes here"
    with httpz.Client() as client:
        resp = client.post(POST_URL, data=body)
        print_response(resp)
        data = resp.json()
        assert len(data["data"]) > 0
    print(f"    PASS")


def test_json_with_custom_headers():
    print("[12] POST JSON with custom headers")
    payload = {"test": "data"}
    with httpz.Client() as client:
        resp = client.post(
            POST_URL,
            json=payload,
            headers={"X-Request-Id": "abc-123", "Authorization": "Bearer token"},
        )
        print_response(resp)
        data = resp.json()
        assert data["json"] == payload
        assert data["headers"].get("X-Request-Id") == "abc-123"
        assert data["headers"].get("Authorization") == "Bearer token"
    print(f"    PASS")


def test_large_json():
    print("[13] POST large JSON payload")
    payload = {"items": [{"id": i, "value": f"item-{i}" * 10} for i in range(100)]}
    with httpz.Client() as client:
        resp = client.post(POST_URL, json=payload)
        data = resp.json()
        print(f"    Status: {resp.status_code} | HTTP: {resp.http_version}")
        print(f"    URL: {resp.url}")
        print(f"    Sent {len(json.dumps(payload))} bytes of JSON")
        print(f"    Received {len(data['json']['items'])} items")
        print(f"    First item: {data['json']['items'][0]}")
        print(f"    Last item:  {data['json']['items'][-1]}")
    print(f"    PASS")


def test_put_json():
    print("[14] PUT with JSON body")
    payload = {"action": "update", "field": "name", "value": "new-name"}
    with httpz.Client() as client:
        resp = client.put("https://httpbin.org/put", json=payload)
        print_response(resp)
        data = resp.json()
        assert data["json"] == payload
    print(f"    PASS")


def test_patch_json():
    print("[15] PATCH with JSON body")
    payload = {"op": "replace", "path": "/name", "value": "patched"}
    with httpz.Client() as client:
        resp = client.patch("https://httpbin.org/patch", json=payload)
        print_response(resp)
        data = resp.json()
        assert data["json"] == payload
    print(f"    PASS")


def main():
    tests = [
        test_json_simple,
        test_json_nested,
        test_json_types,
        test_json_unicode,
        test_json_empty,
        test_form_data_simple,
        test_form_data_special_chars,
        test_form_data_empty_value,
        test_raw_string_body,
        test_raw_bytes_body,
        test_bytes_via_data,
        test_json_with_custom_headers,
        test_large_json,
        test_put_json,
        test_patch_json,
    ]

    print("=" * 60)
    print("  httpz — POST Data Tests")
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
