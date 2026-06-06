#!/usr/bin/env python3
import os
import re
import sys

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
ARCH_DOC = os.path.join(ROOT, "docs", "ARCHITECTURE.md")


def extract_paths(text: str):
    # naive: find backticked paths like `app/fastapi_routes/`
    return re.findall(r"`([^`]+)`", text)


def main():
    if not os.path.exists(ARCH_DOC):
        print(f"ARCHITECTURE.md not found at {ARCH_DOC}")
        return 1
    with open(ARCH_DOC, "r", encoding="utf-8") as f:
        content = f.read()
    candidates = extract_paths(content)
    # filter plausible directory-like entries
    candidates = [p for p in candidates if "/" in p or p.endswith(".py")]
    missing = []
    for p in sorted(set(candidates)):
        abs_p = os.path.join(ROOT, p)
        if not os.path.exists(abs_p):
            missing.append(p)
    if missing:
        print("ARCHITECTURE.md references missing paths:")
        for m in missing:
            print(" -", m)
        return 2
    print("ARCHITECTURE.md directory references OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
