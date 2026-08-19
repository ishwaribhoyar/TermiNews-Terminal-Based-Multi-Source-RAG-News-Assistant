"""
run.py — Top-level entry point for Terminal News Assistant.

Usage:
    python run.py
"""

import os
import sys


def _load_env_file() -> None:
    """
    Load environment variables from .env if present.
    Does not overwrite explicitly set environment variables.
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ and val:
                    os.environ[key] = val
    except Exception:
        pass


def _configure_utf8() -> None:
    """
    Attempt to switch stdout to UTF-8 on Windows so special characters
    render correctly.  Fails silently — main.py has its own ASCII fallback.
    """
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def main() -> None:
    _load_env_file()
    _configure_utf8()
    try:
        from terminal_news_assistant.main import run
        run()
    except ImportError as exc:
        print(
            f"[ERROR] Could not import terminal_news_assistant: {exc}\n"
            "Make sure you have activated the virtual environment and run:\n"
            "    pip install -r requirements.txt"
        )
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Unexpected startup error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
