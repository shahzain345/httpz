# Comparing results from both the libraries 

# chrome146

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import httpz 
from curl_cffi.requests import Session

def httpz_test():
    with httpz.Client(impersonate="firefox151") as client:
        resp = client.get("https://tls.peet.ws/api/all").json()
        return resp

def curlcffi_test():
    with Session(impersonate="chrome146") as session:
        resp = session.get("https://tls.peet.ws/api/all").json()
        return resp
    
if __name__ == "__main__":
    resp_httpz = httpz_test()
    print(f"Response from httpz: {resp_httpz}")
    resp_curlcffi = curlcffi_test()
    print(f"Response from curl_cffi: {resp_curlcffi}")

    print(f"Are both values the same: {resp_httpz == resp_curlcffi}")