"""W3 TEAM: console entrypoint (protonai command)."""
from __future__ import annotations


def main():
    from tools.version import __version__
    print(f"ProtonAI {__version__} — serving on :8000")
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
