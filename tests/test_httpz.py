"""
httpz manual test script.

Run: python tests/test_httpz.py
"""

import asyncio
import json
import sys
import os

# Add parent directory to path so httpz can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpz


def print_response(resp):
    print(f"    response.json() = {json.dumps(resp.json(), indent=6, ensure_ascii=False)}")


def test_basic_get():
    print("[1] Basic GET request")
    resp = httpz.get("https://httpbin.org/get")
    print_response(resp)
    assert resp.status_code == 200
    assert resp.ok
    assert resp.is_success
    data = resp.json()
    assert data["url"] == "https://httpbin.org/get"
    print(f"    PASS")


def test_post_json():
    print("[2] POST with JSON body")
    with httpz.Client() as client:
        resp = client.post("https://httpbin.org/post", json={"key": "value", "num": 42})
        print_response(resp)
        data = resp.json()
        assert data["json"] == {"key": "value", "num": 42}
        assert "application/json" in data["headers"].get("Content-Type", "")
    print(f"    PASS")


def test_post_form():
    print("[3] POST with form data")
    with httpz.Client() as client:
        resp = client.post("https://httpbin.org/post", data={"name": "httpz", "version": "0.1"})
        print_response(resp)
        data = resp.json()
        assert data["form"] == {"name": "httpz", "version": "0.1"}
    print(f"    PASS")


def test_custom_headers():
    print("[4] Custom headers")
    with httpz.Client() as client:
        resp = client.get("https://httpbin.org/headers", headers={"X-Custom": "httpz-test"})
        print_response(resp)
        data = resp.json()
        assert data["headers"].get("X-Custom") == "httpz-test"
    print(f"    PASS")


def test_query_params():
    print("[5] Query parameters")
    with httpz.Client() as client:
        resp = client.get("https://httpbin.org/get", params={"foo": "bar", "n": "1"})
        print_response(resp)
        data = resp.json()
        assert data["args"]["foo"] == "bar"
        assert data["args"]["n"] == "1"
    print(f"    PASS")


def test_status_codes():
    print("[6] Status code properties")
    with httpz.Client() as client:
        r200 = client.get("https://httpbin.org/status/200")
        print(f"    200 response.json() = N/A (empty body)")
        print(f"    200: ok={r200.ok} is_success={r200.is_success}")
        assert r200.ok and r200.is_success

        r404 = client.get("https://httpbin.org/status/404")
        print(f"    404: ok={r404.ok} is_client_error={r404.is_client_error}")
        assert not r404.ok and r404.is_client_error

        r500 = client.get("https://httpbin.org/status/500")
        print(f"    500: ok={r500.ok} is_server_error={r500.is_server_error}")
        assert not r500.ok and r500.is_server_error
    print(f"    PASS")


def test_raise_for_status():
    print("[7] raise_for_status()")
    with httpz.Client() as client:
        resp = client.get("https://httpbin.org/status/500")
        try:
            resp.raise_for_status()
            assert False, "Should have raised"
        except httpz.HTTPStatusError as e:
            print(f"    Caught: {e}")

        resp = client.get("https://httpbin.org/status/200")
        resp.raise_for_status()
        print(f"    200 did not raise")
    print(f"    PASS")


def test_ja3_fingerprint():
    print("[8] JA3 fingerprint")
    ja3 = "772,4865-4867-4866-49195-49199-52393-52392-49196-49200-49162-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-34-18-51-43-13-45-28-27-65037,4588-29-23-24-25-256-257,0"
    with httpz.Client(ja3=ja3) as client:
        resp = client.get("https://tools.scrapfly.io/api/fp/ja3")
        print_response(resp)
        data = resp.json()
        returned = data.get("ja3")
        match = returned == ja3
        print(f"    Match: {match}")
        assert match, f"JA3 mismatch"
    print(f"    PASS")


def test_browser_presets():
    print("[9] Browser presets")
    for browser in [httpz.CHROME, httpz.FIREFOX]:
        with httpz.Client(browser=browser) as client:
            resp = client.get("https://httpbin.org/get")
            print(f"    {browser}: response.json() = {json.dumps(resp.json(), indent=6)}")
            assert resp.status_code == 200
    print(f"    PASS")


def test_session_headers():
    print("[10] Session-level default headers")
    with httpz.Client(headers={"User-Agent": "httpz/0.1", "Accept": "application/json"}) as client:
        resp = client.get("https://httpbin.org/headers")
        print_response(resp)
        data = resp.json()
        assert data["headers"].get("User-Agent") == "httpz/0.1"
        assert data["headers"].get("Accept") == "application/json"
    print(f"    PASS")


def test_put_patch_delete():
    print("[11] PUT / PATCH / DELETE")
    with httpz.Client() as client:
        resp = client.put("https://httpbin.org/put", json={"action": "update"})
        print(f"    PUT response.json() = {json.dumps(resp.json(), indent=6)}")
        assert resp.status_code == 200
        assert resp.json()["json"] == {"action": "update"}

        resp = client.patch("https://httpbin.org/patch", json={"field": "new"})
        print(f"    PATCH response.json() = {json.dumps(resp.json(), indent=6)}")
        assert resp.status_code == 200
        assert resp.json()["json"] == {"field": "new"}

        resp = client.delete("https://httpbin.org/delete")
        print(f"    DELETE response.json() = {json.dumps(resp.json(), indent=6)}")
        assert resp.status_code == 200
    print(f"    PASS")


def test_response_text():
    print("[12] Response .text and .content")
    with httpz.Client() as client:
        resp = client.get("https://httpbin.org/html")
        print(f"    response.text = {resp.text[:200]}...")
        assert isinstance(resp.content, bytes)
        assert isinstance(resp.text, str)
        assert "<html>" in resp.text.lower() or "herman melville" in resp.text.lower()
    print(f"    PASS")


def test_async_client():
    print("[13] AsyncClient")

    async def run():
        async with httpz.AsyncClient() as client:
            resp = await client.get("https://httpbin.org/get")
            print(f"    Async GET response.json() = {json.dumps(resp.json(), indent=6)}")
            assert resp.status_code == 200

            resp = await client.post("https://httpbin.org/post", json={"async": True})
            print(f"    Async POST response.json() = {json.dumps(resp.json(), indent=6)}")
            assert resp.json()["json"] == {"async": True}

            # Concurrent requests
            tasks = [client.get(f"https://httpbin.org/get?n={i}") for i in range(5)]
            results = await asyncio.gather(*tasks)
            codes = [r.status_code for r in results]
            print(f"    Concurrent (5 requests): status_codes={codes}")
            assert all(c == 200 for c in codes)

    asyncio.run(run())
    print(f"    PASS")


def test_h2_fingerprint():
    print("[14] HTTP/2 (Akamai) fingerprint")
    h2fp = "1:65536;2:0;3:1000;4:6291456;6:262144|15663105|0|m,s,a,p"
    with httpz.Client(h2_fingerprint=h2fp) as client:
        resp = client.get("https://httpbin.org/get")
        print_response(resp)
    print(f"    PASS")


def main():
    tests = [
        test_basic_get,
        test_post_json,
        test_post_form,
        test_custom_headers,
        test_query_params,
        test_status_codes,
        test_raise_for_status,
        test_ja3_fingerprint,
        test_browser_presets,
        test_session_headers,
        test_put_patch_delete,
        test_response_text,
        test_async_client,
        test_h2_fingerprint,
    ]

    print("=" * 60)
    print(f"  httpz v{httpz.__version__} — Test Suite")
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
