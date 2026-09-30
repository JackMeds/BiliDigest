#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.bili_migrate import migrate_output_tree


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy BiliDigest output into macOS runtime directories")
    parser.add_argument("--root", type=Path, default=None, help="BiliDigest repository root")
    parser.add_argument("--stamp", default=None, help="Migration stamp for renamed output directory")
    args = parser.parse_args()
    result = migrate_output_tree(
        root=args.root or ROOT,
        stamp=args.stamp or time.strftime("%Y%m%d-%H%M%S"),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
