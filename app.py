import os, base64, binascii, time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import pyotp
from datetime import datetime, timezone

DATA_PATH = Path("/data")
SEED_FILE = DATA_PATH / "seed.txt"
PRIVATE_KEY_PATH = Path("/app/student_private.pem") if Path("/app/student_private.pem").exists() else Path("student_private.pem")

app = FastAPI()

class EncryptedSeedIn(BaseModel):
    encrypted_seed: str

class VerifyIn(BaseModel):
    code: str

def load_private_key():
    pem = PRIVATE_KEY_PATH.read_bytes()
    return serialization.load_pem_private_key(pem, password=None)

def decrypt_seed_b64(encrypted_seed_b64: str) -> str:
    try:
        ciphertext = base64.b64decode(encrypted_seed_b64)
    except binascii.Error:
        raise ValueError("encrypted_seed is not valid base64")
    private_key = load_private_key()
    plain = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    seed = plain.decode("utf-8").strip()
    if len(seed) != 64 or any(c not in "0123456789abcdef" for c in seed):
        raise ValueError("Decrypted seed invalid format")
    return seed

def save_seed(hex_seed: str):
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    SEED_FILE.write_text(hex_seed)
    try:
        os.chmod(SEED_FILE, 0o600)
    except Exception:
        pass

def read_seed() -> str:
    if not SEED_FILE.exists():
        raise FileNotFoundError("Seed not found")
    s = SEED_FILE.read_text().strip()
    if len(s) != 64:
        raise ValueError("Invalid seed length")
    return s

def hex_to_base32(hex_seed: str) -> str:
    raw = bytes.fromhex(hex_seed)
    return base64.b32encode(raw).decode("utf-8")

def generate_totp(hex_seed: str) -> str:
    b32 = hex_to_base32(hex_seed)
    totp = pyotp.TOTP(b32, digits=6, interval=30, digest='sha1')
    return totp.now()

def totp_time_remaining() -> int:
    period = 30
    return period - (int(time.time()) % period)

def verify_totp(hex_seed: str, code: str, valid_window: int = 1) -> bool:
    b32 = hex_to_base32(hex_seed)
    totp = pyotp.TOTP(b32, digits=6, interval=30, digest='sha1')
    return totp.verify(code, valid_window=valid_window)

@app.post("/decrypt-seed")
async def decrypt_seed(payload: EncryptedSeedIn):
    try:
        seed = decrypt_seed_b64(payload.encrypted_seed)
        save_seed(seed)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Decryption failed", "detail": str(e)})

@app.get("/generate-2fa")
async def generate_2fa():
    try:
        seed = read_seed()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail={"error": "Seed not decrypted yet"})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Seed read error", "detail": str(e)})
    try:
        code = generate_totp(seed)
        valid_for = totp_time_remaining()
        return {"code": code, "valid_for": valid_for}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "TOTP generation failed", "detail": str(e)})

@app.post("/verify-2fa")
async def verify_2fa(payload: VerifyIn):
    if not payload.code:
        raise HTTPException(status_code=400, detail={"error": "Missing code"})
    try:
        seed = read_seed()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail={"error": "Seed not decrypted yet"})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Seed read error", "detail": str(e)})
    try:
        valid = verify_totp(seed, payload.code, valid_window=1)
        return {"valid": bool(valid)}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Verification error", "detail": str(e)})

@app.get("/health")
async def health():
    return {"status": "ok", "utc": datetime.now(timezone.utc).isoformat()}
