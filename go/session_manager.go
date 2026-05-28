package main

import (
	"sync"
	"sync/atomic"

	"github.com/Noooste/azuretls-client"
)

var (
	sessionMap   = make(map[int64]*azuretls.Session)
	sessionMutex sync.RWMutex
	nextID       int64
)

func newSession() int64 {
	id := atomic.AddInt64(&nextID, 1)
	session := azuretls.NewSession()

	sessionMutex.Lock()
	sessionMap[id] = session
	sessionMutex.Unlock()

	return id
}

func getSession(id int64) (*azuretls.Session, bool) {
	sessionMutex.RLock()
	s, ok := sessionMap[id]
	sessionMutex.RUnlock()
	return s, ok
}

func deleteSession(id int64) {
	sessionMutex.Lock()
	if s, ok := sessionMap[id]; ok {
		s.Close()
		delete(sessionMap, id)
	}
	sessionMutex.Unlock()
}
