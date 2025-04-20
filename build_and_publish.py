#!/usr/bin/env python3
"""
Build and publish the httpz package to PyPI.

This script performs the following steps:
1. Clean up previous builds
2. Build the library for the current platform
3. Build the Python package
4. Upload to PyPI (if requested)

Usage:
    python build_and_publish.py [--upload]

Options:
    --upload    Upload the package to PyPI after building
"""

import os
import sys
import subprocess
import shutil
import argparse


def run_command(cmd, cwd=None):
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def clean():
    """Clean up previous builds."""
    print("\n=== Cleaning up previous builds ===")
    
    # Remove build artifacts
    for path in ["dist", "build", "*.egg-info"]:
        try:
            if os.path.exists(path):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                print(f"Removed {path}")
        except Exception as e:
            print(f"Failed to remove {path}: {e}")
    
    # Run make clean
    return run_command(["make", "clean"])


def build_library():
    """Build the shared library."""
    print("\n=== Building shared library ===")
    return run_command(["make"])


def build_package():
    """Build the Python package."""
    print("\n=== Building Python package ===")
    
    # Install build dependencies
    if not run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "build", "twine"]):
        return False
    
    # Build the package
    return run_command([sys.executable, "-m", "build"])


def upload_to_pypi():
    """Upload the package to PyPI."""
    print("\n=== Uploading to PyPI ===")
    
    # Check if twine is installed
    if not run_command([sys.executable, "-m", "pip", "show", "twine"]):
        print("Twine is not installed. Installing...")
        if not run_command([sys.executable, "-m", "pip", "install", "twine"]):
            return False
    
    # Upload to PyPI
    return run_command([sys.executable, "-m", "twine", "upload", "dist/*"])


def main():
    parser = argparse.ArgumentParser(description="Build and publish the httpz package.")
    parser.add_argument("--upload", action="store_true", 
                        help="Upload the package to PyPI after building")
    args = parser.parse_args()
    
    # Clean up
    if not clean():
        print("Failed to clean up previous builds")
        return 1
    
    # Build the library
    if not build_library():
        print("Failed to build shared library")
        return 1
    
    # Build the package
    if not build_package():
        print("Failed to build Python package")
        return 1
    
    # Upload to PyPI if requested
    if args.upload:
        if not upload_to_pypi():
            print("Failed to upload to PyPI")
            return 1
        print("\n=== Package successfully uploaded to PyPI ===")
    else:
        print("\n=== Package successfully built ===")
        print("To upload to PyPI, run: python build_and_publish.py --upload")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 