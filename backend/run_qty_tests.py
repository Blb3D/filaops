import subprocess
import sys

result = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        "tests/api/test_operation_status.py::TestQuantityValidation",
        "-v", "--tb=short"
    ],
    capture_output=True,
    text=True,
    cwd=r"C:\repos\filaops\backend"
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")
