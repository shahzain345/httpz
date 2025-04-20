package main

import "C"

// Build with:
// go build -buildmode=c-shared -o libazuretls.so client.go
// This will generate libazuretls.so and libazuretls.h

// Include exported functions from client.go
