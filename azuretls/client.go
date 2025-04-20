package main

/*
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
*/
import "C"

import (
	"encoding/json"
	"fmt"
	"sync"
	"unsafe"

	"github.com/Noooste/azuretls-client"
)

// SessionManager manages sessions to avoid issues with cgo pointers
type SessionManager struct {
	mutex    sync.Mutex
	sessions map[int64]*azuretls.Session
	nextID   int64
}

var manager = &SessionManager{
	sessions: make(map[int64]*azuretls.Session),
}

//export NewSession
func NewSession() C.int64_t {
	session := azuretls.NewSession()

	// Check if session is nil
	if session == nil {
		return C.int64_t(0)
	}

	manager.mutex.Lock()
	defer manager.mutex.Unlock()

	id := manager.nextID
	// Ensure we never return 0 as an ID (which is used as an error code)
	if id == 0 {
		id = 1
	}
	manager.nextID = id + 1
	manager.sessions[id] = session

	return C.int64_t(id)
}

//export ApplyJA3
func ApplyJA3(sessionID C.int64_t, ja3Str *C.char, browserStr *C.char) *C.char {
	manager.mutex.Lock()
	session, exists := manager.sessions[int64(sessionID)]
	manager.mutex.Unlock()

	if !exists {
		return C.CString("Error: invalid session ID")
	}

	ja3 := C.GoString(ja3Str)
	browser := C.GoString(browserStr)

	var browserName string
	switch browser {
	case "Chrome":
		browserName = "chrome"
	case "Safari":
		browserName = "safari"
	case "Firefox":
		browserName = "firefox"
	case "Opera":
		browserName = "opera"
	default:
		browserName = "chrome"
	}

	err := session.ApplyJa3(ja3, browserName)
	if err != nil {
		return C.CString(fmt.Sprintf("Error: %v", err))
	}
	return C.CString("")
}

//export SetProxy
func SetProxy(sessionID C.int64_t, proxyStr *C.char) *C.char {
	manager.mutex.Lock()
	session, exists := manager.sessions[int64(sessionID)]
	manager.mutex.Unlock()

	if !exists {
		return C.CString("Error: invalid session ID")
	}

	proxy := C.GoString(proxyStr)

	err := session.SetProxy(proxy)
	if err != nil {
		return C.CString(fmt.Sprintf("Error: %v", err))
	}
	return C.CString("")
}

//export SetOrderedHeaders
func SetOrderedHeaders(sessionID C.int64_t, headersStr *C.char) *C.char {
	manager.mutex.Lock()
	session, exists := manager.sessions[int64(sessionID)]
	manager.mutex.Unlock()

	if !exists {
		return C.CString("Error: invalid session ID")
	}

	headersJSON := C.GoString(headersStr)

	var headers [][]string
	err := json.Unmarshal([]byte(headersJSON), &headers)
	if err != nil {
		return C.CString(fmt.Sprintf("Error unmarshaling headers: %v", err))
	}

	orderedHeaders := make(azuretls.OrderedHeaders, len(headers))
	for i, h := range headers {
		if len(h) >= 2 {
			orderedHeaders[i] = []string{h[0], h[1]}
		}
	}

	session.OrderedHeaders = orderedHeaders
	return C.CString("")
}

//export DoRequest
func DoRequest(sessionID C.int64_t, methodStr *C.char, urlStr *C.char, headersStr *C.char, bodyStr *C.char) *C.char {
	manager.mutex.Lock()
	session, exists := manager.sessions[int64(sessionID)]
	manager.mutex.Unlock()

	if !exists {
		return C.CString(`{"error": "invalid session ID"}`)
	}

	method := C.GoString(methodStr)
	url := C.GoString(urlStr)
	headersJSON := C.GoString(headersStr)
	body := C.GoString(bodyStr)

	var headers map[string]string
	if headersJSON != "" {
		err := json.Unmarshal([]byte(headersJSON), &headers)
		if err != nil {
			return C.CString(fmt.Sprintf(`{"error": "Error unmarshaling headers: %v"}`, err))
		}
	}

	var resp *azuretls.Response
	var err error

	switch method {
	case "GET":
		resp, err = session.Get(url)
	case "POST":
		resp, err = session.Post(url, body, headers)
	case "PUT":
		resp, err = session.Put(url, body, headers)
	case "DELETE":
		resp, err = session.Delete(url, headers)
	case "HEAD":
		resp, err = session.Head(url)
	case "PATCH":
		resp, err = session.Patch(url, body, headers)
	default:
		return C.CString(`{"error": "Invalid HTTP method"}`)
	}

	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "%v"}`, err))
	}

	// Extract cookies from the map
	cookiesArray := make([]map[string]string, 0)
	for name, value := range resp.Cookies {
		cookieMap := map[string]string{
			"name":  name,
			"value": value,
		}
		cookiesArray = append(cookiesArray, cookieMap)
	}

	result := map[string]interface{}{
		"status_code": resp.StatusCode,
		"headers":     resp.Header,
		"body":        string(resp.Body),
		"cookies":     cookiesArray,
	}

	jsonResult, err := json.Marshal(result)
	if err != nil {
		return C.CString(fmt.Sprintf(`{"error": "Failed to marshal response: %v"}`, err))
	}

	// Convert to C string - this needs to be freed by the caller
	return C.CString(string(jsonResult))
}

//export CloseSession
func CloseSession(sessionID C.int64_t) {
	manager.mutex.Lock()
	defer manager.mutex.Unlock()

	session, exists := manager.sessions[int64(sessionID)]
	if exists {
		session.Close()
		delete(manager.sessions, int64(sessionID))
	}
}

//export FreeString
func FreeString(str *C.char) {
	C.free(unsafe.Pointer(str))
}

func main() {}
