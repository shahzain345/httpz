#!/usr/bin/env bash
# Builds the httpz_bridge shared library for macOS (both architectures).
# Works on either an Intel (x86_64) or Apple Silicon (arm64) Mac.
# Requirements: Go + Xcode Command Line Tools (`xcode-select --install`).
set -euo pipefail

cd "$(dirname "$0")"

OUT_DIR="../httpz/_libs"
mkdir -p "$OUT_DIR"

command -v go    >/dev/null || { echo "error: go not in PATH"; exit 1; }
command -v clang >/dev/null || { echo "error: clang not in PATH (run: xcode-select --install)"; exit 1; }

export CGO_ENABLED=1

build() {
    local goarch="$1" clang_arch="$2" out="$3"
    echo ">>> Building darwin/${goarch} -> ${out}"
    GOOS=darwin GOARCH="$goarch" CC="clang -arch ${clang_arch}" \
        go build -buildmode=c-shared -o "${OUT_DIR}/${out}" .
    echo "    OK $(ls -lh "${OUT_DIR}/${out}" | awk '{print $5}')"
}

build amd64 x86_64 httpz_bridge.dylib
build arm64 arm64  httpz_bridge_arm64.dylib

echo "Build OK:"
echo "  ${OUT_DIR}/httpz_bridge.dylib"
echo "  ${OUT_DIR}/httpz_bridge_arm64.dylib"
