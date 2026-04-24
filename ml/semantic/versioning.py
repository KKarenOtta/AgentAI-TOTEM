from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

FAQ_FILE = Path("data/zoo_faq.json")
VERSIONS_DIR = Path("data/faq_versions")


def save_version():
    if not FAQ_FILE.exists():
        return

    VERSIONS_DIR.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = VERSIONS_DIR / f"faq_{ts}.json"

    out.write_text(FAQ_FILE.read_text(), encoding="utf-8")

    print(f"Versão salva: {out}")


if __name__ == "__main__":
    save_version()
