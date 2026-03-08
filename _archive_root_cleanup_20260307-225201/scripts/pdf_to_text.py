from __future__ import annotations

import sys
from pathlib import Path

from pdfminer.high_level import extract_text


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: pdf_to_text.py <input.pdf> [output.txt]")
        return 2
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    text = extract_text(str(inp))
    if out:
        out.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
