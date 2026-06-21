#!/usr/bin/env python3
"""Verify imports and optional API connectivity — run after `pip install -r requirements.txt`."""

from __future__ import annotations

import importlib
import os
import sys


def check_module(name: str) -> None:
    importlib.import_module(name)
    print(f"ok: import {name}")


def main() -> int:
    print("Python:", sys.version)
    if sys.version_info >= (3, 13):
        print(
            "warn: Python 3.13+ may fail to install chromadb on some platforms; use 3.12.x (see .python-version)."
        )

    for mod in (
        "openai",
        "tiktoken",
        "pydantic",
        "pydantic_settings",
        "dotenv",
        "httpx",
        "fastapi",
    ):
        check_module(mod)

    try:
        check_module("chromadb")
    except Exception as exc:  # noqa: BLE001 — diagnostic only
        print(f"warn: chromadb import failed ({exc!s}) — fix env Python version or reinstall chromadb.")

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    import lumen  # noqa: PLC0415

    print(f"ok: lumen package version {lumen.__version__}")

    if os.environ.get("OPENAI_API_KEY"):
        print("ok: OPENAI_API_KEY is set (length hidden)")
    else:
        print("note: OPENAI_API_KEY not set — optional if you use DeepSeek for chat.")

    if os.environ.get("DEEPSEEK_API_KEY"):
        print("ok: DEEPSEEK_API_KEY is set (length hidden)")
    else:
        print("note: DEEPSEEK_API_KEY not set — optional unless LUMEN_LLM_PROVIDER=deepseek.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
