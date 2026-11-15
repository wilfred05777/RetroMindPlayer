"""Windowed PyInstaller entry point; no source-tree imports at runtime."""
from retromind.main import main

if __name__ == '__main__':
    raise SystemExit(main())
