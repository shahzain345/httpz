from __future__ import annotations

import ctypes
import json
import os
import platform
from pathlib import Path
from typing import Optional

from .exceptions import BridgeError, TransportError, TimeoutError, ProxyError, ConnectionError, TooManyRedirects


def _find_library() -> str:
    """Locate the shared library for the current platform."""
    # Check environment variable override first
    env_path = os.environ.get("HTTPZ_LIB_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    lib_dir = Path(__file__).parent / "_libs"
    system = platform.system()

    if system == "Windows":
        name = "httpz_bridge.dll"
    elif system == "Linux":
        name = "httpz_bridge.so"
    elif system == "Darwin":
        machine = platform.machine().lower()
        if machine == "arm64":
            name = "httpz_bridge_arm64.dylib"
        else:
            name = "httpz_bridge.dylib"
    else:
        raise TransportError(f"Unsupported platform: {system}")

    path = lib_dir / name
    if not path.exists():
        raise TransportError(
            f"Shared library not found at {path}. "
            "Build it with: cd go && build.bat (Windows) or make (Linux/macOS)"
        )
    return str(path)


def _classify_error(error_msg: str):
    """Map Go error strings to specific Python exceptions."""
    msg = error_msg.lower()
    if "timeout" in msg or "deadline" in msg:
        return TimeoutError(error_msg)
    if "proxy" in msg:
        return ProxyError(error_msg)
    if "too many redirect" in msg or "redirect" in msg and "max" in msg:
        return TooManyRedirects(error_msg)
    if "no such host" in msg or "connection refused" in msg or "dial" in msg:
        return ConnectionError(error_msg)
    return BridgeError(error_msg)


class Bridge:
    """
    Low-level FFI bridge to the Go shared library.

    Thread-safe: the underlying Go code uses mutexes.
    Singleton: one bridge per process.
    """

    _instance: Optional[Bridge] = None

    def __new__(cls):
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._load()
            cls._instance = inst
        return cls._instance

    def _load(self):
        lib_path = _find_library()

        if platform.system() == "Windows":
            self._lib = ctypes.CDLL(lib_path, winmode=0)
        else:
            self._lib = ctypes.CDLL(lib_path)

        # All functions returning *C.char use c_void_p to preserve the raw
        # pointer so we can call FreeMemory on it. Using c_char_p would cause
        # ctypes to silently copy the string and discard the pointer → leak.

        # FreeMemory(ptr *C.char)
        self._lib.FreeMemory.argtypes = [ctypes.c_void_p]
        self._lib.FreeMemory.restype = None

        # CreateSession(configJSON *C.char) -> *C.char
        self._lib.CreateSession.argtypes = [ctypes.c_char_p]
        self._lib.CreateSession.restype = ctypes.c_void_p

        # CloseSession(sessionID C.longlong)
        self._lib.CloseSession.argtypes = [ctypes.c_longlong]
        self._lib.CloseSession.restype = None

        # Request(sessionID C.longlong, requestJSON *C.char) -> *C.char
        self._lib.Request.argtypes = [ctypes.c_longlong, ctypes.c_char_p]
        self._lib.Request.restype = ctypes.c_void_p

        # ConfigureSession(sessionID C.longlong, configJSON *C.char) -> *C.char
        self._lib.ConfigureSession.argtypes = [ctypes.c_longlong, ctypes.c_char_p]
        self._lib.ConfigureSession.restype = ctypes.c_void_p

        # ApplyJA3(sessionID C.longlong, ja3 *C.char, navigator *C.char) -> *C.char
        self._lib.ApplyJA3.argtypes = [ctypes.c_longlong, ctypes.c_char_p, ctypes.c_char_p]
        self._lib.ApplyJA3.restype = ctypes.c_void_p

        # ApplyHTTP2Fingerprint(sessionID C.longlong, fp *C.char) -> *C.char
        self._lib.ApplyHTTP2Fingerprint.argtypes = [ctypes.c_longlong, ctypes.c_char_p]
        self._lib.ApplyHTTP2Fingerprint.restype = ctypes.c_void_p

        # SetProxy(sessionID C.longlong, proxyURL *C.char) -> *C.char
        self._lib.SetProxy.argtypes = [ctypes.c_longlong, ctypes.c_char_p]
        self._lib.SetProxy.restype = ctypes.c_void_p

        # ClearProxy(sessionID C.longlong) -> *C.char
        self._lib.ClearProxy.argtypes = [ctypes.c_longlong]
        self._lib.ClearProxy.restype = ctypes.c_void_p

    def _call(self, func_name: str, *args) -> dict:
        """Call a Go function, parse JSON response, free the Go-allocated memory."""
        func = getattr(self._lib, func_name)
        ptr = func(*args)
        if not ptr:
            raise TransportError(f"Go function {func_name} returned NULL")

        try:
            result_bytes = ctypes.string_at(ptr)
            result = json.loads(result_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise TransportError(f"Invalid response from Go bridge: {e}")
        finally:
            self._lib.FreeMemory(ctypes.c_void_p(ptr))

        if result.get("error"):
            raise _classify_error(result["error"])

        return result

    def create_session(self, config: dict = None) -> int:
        config_json = json.dumps(config or {}).encode("utf-8")
        result = self._call("CreateSession", config_json)
        return int(result["data"])

    def close_session(self, session_id: int) -> None:
        self._lib.CloseSession(ctypes.c_longlong(session_id))

    def request(self, session_id: int, request_data: dict) -> dict:
        req_json = json.dumps(request_data).encode("utf-8")
        return self._call("Request", ctypes.c_longlong(session_id), req_json)

    def configure_session(self, session_id: int, config: dict) -> None:
        config_json = json.dumps(config).encode("utf-8")
        self._call("ConfigureSession", ctypes.c_longlong(session_id), config_json)

    def apply_ja3(self, session_id: int, ja3: str, navigator: str) -> None:
        self._call(
            "ApplyJA3",
            ctypes.c_longlong(session_id),
            ja3.encode("utf-8"),
            navigator.encode("utf-8"),
        )

    def apply_h2_fingerprint(self, session_id: int, fingerprint: str) -> None:
        self._call(
            "ApplyHTTP2Fingerprint",
            ctypes.c_longlong(session_id),
            fingerprint.encode("utf-8"),
        )

    def set_proxy(self, session_id: int, proxy_url: str) -> None:
        self._call(
            "SetProxy",
            ctypes.c_longlong(session_id),
            proxy_url.encode("utf-8"),
        )

    def clear_proxy(self, session_id: int) -> None:
        self._call("ClearProxy", ctypes.c_longlong(session_id))
