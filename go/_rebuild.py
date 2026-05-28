import subprocess, os

env = os.environ.copy()
env["PATH"] = r"C:\Program Files\Go\bin;C:\msys64\mingw64\bin;" + env["PATH"]
env["CGO_ENABLED"] = "1"

go_path = r"C:\Program Files\Go\bin\go.exe"

result = subprocess.run(
    [go_path, "build", "-buildmode=c-shared", "-o", r"D:\httpz\httpz\_libs\httpz_bridge.dll", "."],
    cwd=r"D:\httpz\go",
    env=env,
    capture_output=True,
    text=True,
)
print(f"Return code: {result.returncode}")
print(f"stdout: {result.stdout}")
print(f"stderr: {result.stderr}")
