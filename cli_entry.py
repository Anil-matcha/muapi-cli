"""PyInstaller entry point — no relative imports."""
import sys
from muapi.main import _entrypoint

if __name__ == "__main__":
    # Ensure the program name shown in help/usage is always "muapi"
    # regardless of the actual binary filename (e.g. muapi-darwin-arm64)
    sys.argv[0] = "muapi"
    _entrypoint()
