import sys, os, json, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import httpz


async def main():
    async with httpz.AsyncClient(headers={"X-Test-Id": "abc-123", "Authorization": "Bearer token"}) as client:
        resp = await client.post(
            "https://httpbin.org/post",
            json={"test": "data"},
        )
        data = resp.json()
        print("Server received headers:")
        print(json.dumps(data["headers"], indent=2))
        print()
        xrid = data["headers"].get("X-Test-Id")
        auth = data["headers"].get("Authorization")
        print(f"X-Test-Id: {xrid} {'PASS' if xrid == 'abc-123' else 'FAIL'}")
        print(f"Authorization: {auth} {'PASS' if auth == 'Bearer token' else 'FAIL'}")

        client.headers["X-Second-Header"] = "shahzain345"
        # request 2, check if headers are being passed on to all requests.
        resp = await client.post(
            "https://httpbin.org/post",
            json={"test": "data"},
        )
        data = resp.json()
        print("Server received headers:")
        print(json.dumps(data["headers"], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
