package main

/*
#include <stdlib.h>
*/
import "C"

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"
	"unsafe"

	"github.com/Noooste/azuretls-client"
)

// returnJSON marshals any value to a C string. Caller must call FreeMemory.
func returnJSON(v interface{}) *C.char {
	b, err := json.Marshal(v)
	if err != nil {
		errResp, _ := json.Marshal(GenericResult{Error: err.Error()})
		return C.CString(string(errResp))
	}
	return C.CString(string(b))
}

func returnError(msg string) *C.char {
	return returnJSON(GenericResult{Error: msg})
}

func returnOK() *C.char {
	return returnJSON(GenericResult{Success: true})
}

//export FreeMemory
func FreeMemory(ptr *C.char) {
	C.free(unsafe.Pointer(ptr))
}

//export CreateSession
func CreateSession(configJSON *C.char) *C.char {
	id := newSession()

	configStr := C.GoString(configJSON)
	if configStr != "" && configStr != "{}" {
		var cfg SessionConfig
		if err := json.Unmarshal([]byte(configStr), &cfg); err != nil {
			deleteSession(id)
			return returnError("invalid config JSON: " + err.Error())
		}
		s, _ := getSession(id)
		if err := applyConfig(s, &cfg); err != nil {
			deleteSession(id)
			return returnError(err.Error())
		}
	}

	return returnJSON(GenericResult{
		Success: true,
		Data:    fmt.Sprintf("%d", id),
	})
}

//export CloseSession
func CloseSession(sessionID C.longlong) {
	deleteSession(int64(sessionID))
}

//export Request
func Request(sessionID C.longlong, requestJSON *C.char) *C.char {
	s, ok := getSession(int64(sessionID))
	if !ok {
		return returnError("session not found")
	}

	var req BridgeRequest
	if err := json.Unmarshal([]byte(C.GoString(requestJSON)), &req); err != nil {
		return returnError("invalid request JSON: " + err.Error())
	}

	return doRequest(s, &req)
}

//export ConfigureSession
func ConfigureSession(sessionID C.longlong, configJSON *C.char) *C.char {
	s, ok := getSession(int64(sessionID))
	if !ok {
		return returnError("session not found")
	}

	var cfg SessionConfig
	if err := json.Unmarshal([]byte(C.GoString(configJSON)), &cfg); err != nil {
		return returnError("invalid config JSON: " + err.Error())
	}

	if err := applyConfig(s, &cfg); err != nil {
		return returnError(err.Error())
	}
	return returnOK()
}

//export ApplyJA3
func ApplyJA3(sessionID C.longlong, ja3 *C.char, navigator *C.char) *C.char {
	s, ok := getSession(int64(sessionID))
	if !ok {
		return returnError("session not found")
	}
	if err := s.ApplyJa3(C.GoString(ja3), C.GoString(navigator)); err != nil {
		return returnError(err.Error())
	}
	return returnOK()
}

//export ApplyHTTP2Fingerprint
func ApplyHTTP2Fingerprint(sessionID C.longlong, fp *C.char) *C.char {
	s, ok := getSession(int64(sessionID))
	if !ok {
		return returnError("session not found")
	}
	if err := s.ApplyHTTP2(C.GoString(fp)); err != nil {
		return returnError(err.Error())
	}
	return returnOK()
}

//export SetProxy
func SetProxy(sessionID C.longlong, proxyURL *C.char) *C.char {
	s, ok := getSession(int64(sessionID))
	if !ok {
		return returnError("session not found")
	}
	if err := s.SetProxy(C.GoString(proxyURL)); err != nil {
		return returnError(err.Error())
	}
	return returnOK()
}

//export ClearProxy
func ClearProxy(sessionID C.longlong) *C.char {
	s, ok := getSession(int64(sessionID))
	if !ok {
		return returnError("session not found")
	}
	s.Proxy = ""
	return returnOK()
}

// applyConfig applies a SessionConfig to an azuretls.Session.
func applyConfig(s *azuretls.Session, cfg *SessionConfig) error {
	if cfg.Browser != "" {
		s.Browser = cfg.Browser
	}
	if cfg.UserAgent != "" {
		s.UserAgent = cfg.UserAgent
	}
	if cfg.TimeoutMs > 0 {
		s.TimeOut = time.Duration(cfg.TimeoutMs) * time.Millisecond
	}
	if cfg.MaxRedirects > 0 {
		s.MaxRedirects = uint(cfg.MaxRedirects)
	}
	if cfg.InsecureSkip {
		s.InsecureSkipVerify = true
	}
	if cfg.Proxy != "" {
		if err := s.SetProxy(cfg.Proxy); err != nil {
			return fmt.Errorf("proxy error: %w", err)
		}
	}
	if cfg.JA3 != "" {
		navigator := cfg.JA3Navigator
		if navigator == "" {
			navigator = azuretls.Chrome
		}
		if err := s.ApplyJa3(cfg.JA3, navigator); err != nil {
			return fmt.Errorf("ja3 error: %w", err)
		}
	}
	if cfg.H2Fingerprint != "" {
		if err := s.ApplyHTTP2(cfg.H2Fingerprint); err != nil {
			return fmt.Errorf("h2 fingerprint error: %w", err)
		}
	}
	if len(cfg.Headers) > 0 {
		oh := azuretls.OrderedHeaders{}
		for _, pair := range cfg.Headers {
			if len(pair) == 2 {
				oh = append(oh, []string{strings.ToLower(pair[0]), pair[1]})
			}
		}
		s.OrderedHeaders = oh
	}
	return nil
}

// debugPath is read once at startup. When HTTPZ_DEBUG_LOG is unset (the
// default for every shipped build), debugLog is a no-op and never touches the
// filesystem — so we never write request URLs/headers to a user's disk.
var debugPath = os.Getenv("HTTPZ_DEBUG_LOG")

func debugLog(format string, args ...interface{}) {
	if debugPath == "" {
		return
	}
	f, err := os.OpenFile(debugPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return
	}
	defer f.Close()
	fmt.Fprintf(f, format+"\n", args...)
}

// doRequest executes an HTTP request and returns the JSON response.
func doRequest(s *azuretls.Session, req *BridgeRequest) *C.char {
	debugLog("doRequest: method=%s url=%s headersLen=%d contentType=%s", req.Method, req.URL, len(req.Headers), req.ContentType)
	for i, h := range req.Headers {
		debugLog("  req.Headers[%d] = %v", i, h)
	}

	azReq := &azuretls.Request{
		Method: req.Method,
		Url:    req.URL,
	}

	// Per-request headers: copy session's OrderedHeaders and append custom ones.
	// This preserves browser fingerprint / session-level headers while adding
	// request-specific headers on top.
	if len(req.Headers) > 0 {
		merged := make(azuretls.OrderedHeaders, len(s.OrderedHeaders))
		copy(merged, s.OrderedHeaders)
		debugLog("session OrderedHeaders len=%d", len(s.OrderedHeaders))
		for _, pair := range req.Headers {
			if len(pair) == 2 {
				key := strings.ToLower(pair[0])
				// Replace if already present, otherwise append
				found := false
				for i, existing := range merged {
					if existing[0] == key {
						merged[i] = []string{key, pair[1]}
						found = true
						break
					}
				}
				if !found {
					merged = append(merged, []string{key, pair[1]})
				}
			}
		}
		azReq.OrderedHeaders = merged
		debugLog("final azReq.OrderedHeaders: %v", merged)
	}

	// Body
	if req.BodyBase64 != "" {
		decoded, err := base64.StdEncoding.DecodeString(req.BodyBase64)
		if err != nil {
			return returnError("invalid base64 body: " + err.Error())
		}
		azReq.Body = decoded
	} else if req.Body != "" {
		azReq.Body = req.Body
	}

	// Content-Type header
	if req.ContentType != "" {
		if azReq.OrderedHeaders == nil {
			azReq.OrderedHeaders = azuretls.OrderedHeaders{}
		}
		// Override or append content-type
		found := false
		for i, existing := range azReq.OrderedHeaders {
			if strings.ToLower(existing[0]) == "content-type" {
				azReq.OrderedHeaders[i] = []string{"content-type", req.ContentType}
				found = true
				break
			}
		}
		if !found {
			azReq.OrderedHeaders = append(azReq.OrderedHeaders, []string{"content-type", req.ContentType})
		}
	}

	// Timeout
	if req.TimeoutMs > 0 {
		azReq.TimeOut = time.Duration(req.TimeoutMs) * time.Millisecond
	}

	// Redirects
	if req.DisableRedirect {
		azReq.DisableRedirects = true
	}
	if req.MaxRedirects > 0 {
		azReq.MaxRedirects = uint(req.MaxRedirects)
	}

	// Flags
	azReq.InsecureSkipVerify = req.InsecureSkip
	azReq.NoCookie = req.NoCookie
	azReq.ForceHTTP1 = req.ForceHTTP1

	// Execute
	debugLog("PRE-DO azReq.OrderedHeaders: %v", azReq.OrderedHeaders)
	resp, err := s.Do(azReq)

	if err != nil {
		return returnError(err.Error())
	}

	// Build response
	bridgeResp := BridgeResponse{
		StatusCode: resp.StatusCode,
		URL:        resp.Url,
		BodyBase64: base64.StdEncoding.EncodeToString(resp.Body),
		Cookies:    resp.Cookies,
	}

	// Headers — preserve order from http.Header
	if resp.Header != nil {
		for key, vals := range resp.Header {
			for _, v := range vals {
				bridgeResp.Headers = append(bridgeResp.Headers, []string{key, v})
			}
		}
	}

	// Ensure non-nil collections
	if bridgeResp.Headers == nil {
		bridgeResp.Headers = [][]string{}
	}
	if bridgeResp.Cookies == nil {
		bridgeResp.Cookies = make(map[string]string)
	}

	// Protocol version
	if resp.HttpResponse != nil {
		bridgeResp.Proto = resp.HttpResponse.Proto
	}

	return returnJSON(bridgeResp)
}

func main() {}
