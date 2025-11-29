#!/usr/bin/env python3
import subprocess
from pathlib import Path
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

def git_commit_hash():
    out = subprocess.check_output(["git", "rev-parse", "HEAD"])
    return out.decode().strip()

def load_private_key(path: Path):
    pem = path.read_bytes()
    return serialization.load_pem_private_key(pem, password=None)

def load_public_key(path: Path):
    pem = path.read_bytes()
    return serialization.load_pem_public_key(pem)

def sign_message(message: str, private_key) -> bytes:
    signature = private_key.sign(
        message.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature

def encrypt_with_public_key(data: bytes, public_key) -> bytes:
    cipher = public_key.encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return cipher

def main():
    commit_hash = git_commit_hash()
    priv = load_private_key(Path("student_private.pem"))
    instr_pub = load_public_key(Path("instructor_public.pem"))
    sig = sign_message(commit_hash, priv)
    enc = encrypt_with_public_key(sig, instr_pub)
    enc_b64 = base64.b64encode(enc).decode()
    print("Commit Hash:", commit_hash)
    print("Encrypted Signature (base64):")
    print(enc_b64)

if __name__ == "__main__":
    main()
