#!/usr/bin/env python3
import sys
from pathlib import Path
import base64
from datetime import datetime, timezone

DATA_PATH = Path("/data")
SEED_FILE = DATA_PATH / "seed.txt"

def hex_to_base32(hex_seed: str) -> str:
    raw = bytes.fromhex(hex_seed)
    return base64.b32encode(raw).decode("utf-8")

def generate_totp(hex_seed: str) -> str:
    import pyotp
    b32 = hex_to_base32(hex_seed)
    totp = pyotp.TOTP(b32, digits=6, interval=30, digest='sha1')
    return totp.now()

def main():
    try:
        if not SEED_FILE.exists():
            print("ERROR: seed file not found", file=sys.stderr)
            return 2
        seed = SEED_FILE.read_text().strip()
        code = generate_totp(seed)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{ts} - 2FA Code: {code}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3

if __name__ == "__main__":
    exit(main())
