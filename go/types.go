package main

// BridgeRequest is the JSON sent from Python to Go for HTTP requests.
type BridgeRequest struct {
	URL             string     `json:"url"`
	Method          string     `json:"method"`
	Headers         [][]string `json:"headers,omitempty"`
	Body            string     `json:"body,omitempty"`
	BodyBase64      string     `json:"body_base64,omitempty"`
	ContentType     string     `json:"content_type,omitempty"`
	TimeoutMs       int        `json:"timeout_ms,omitempty"`
	MaxRedirects    int        `json:"max_redirects,omitempty"`
	DisableRedirect bool       `json:"disable_redirect,omitempty"`
	InsecureSkip    bool       `json:"insecure_skip,omitempty"`
	NoCookie        bool       `json:"no_cookie,omitempty"`
	ForceHTTP1      bool       `json:"force_http1,omitempty"`
}

// BridgeResponse is the JSON returned from Go to Python.
type BridgeResponse struct {
	StatusCode int               `json:"status_code"`
	Headers    [][]string        `json:"headers"`
	BodyBase64 string            `json:"body_base64"`
	Cookies    map[string]string `json:"cookies"`
	URL        string            `json:"url"`
	Proto      string            `json:"proto,omitempty"`
	Error      string            `json:"error,omitempty"`
}

// SessionConfig is JSON sent when creating or configuring a session.
type SessionConfig struct {
	Browser       string     `json:"browser,omitempty"`
	JA3           string     `json:"ja3,omitempty"`
	JA3Navigator  string     `json:"ja3_navigator,omitempty"`
	H2Fingerprint string     `json:"h2_fingerprint,omitempty"`
	Proxy         string     `json:"proxy,omitempty"`
	Headers       [][]string `json:"headers,omitempty"`
	UserAgent     string     `json:"user_agent,omitempty"`
	TimeoutMs     int        `json:"timeout_ms,omitempty"`
	MaxRedirects  int        `json:"max_redirects,omitempty"`
	InsecureSkip  bool       `json:"insecure_skip,omitempty"`
}

// GenericResult is a simple success/error response.
type GenericResult struct {
	Success bool   `json:"success"`
	Error   string `json:"error,omitempty"`
	Data    string `json:"data,omitempty"`
}
