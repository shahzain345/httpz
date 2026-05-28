import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import httpz

def main():
    ja3 = "772,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,27-65281-11-45-35-16-65037-10-23-18-0-13-5-43-51-17613,4588-29-23-24,0"
    browser = "chrome"
    client = httpz.Client(ja3=ja3, browser=browser)
    resp = client.get("https://tools.scrapfly.io/api/fp/ja3")
    print(resp.json()["ja3"], resp.json()["ja3"] == ja3)

if __name__ == "__main__":
    main()