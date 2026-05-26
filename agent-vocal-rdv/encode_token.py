"""Encode token.json + credentials.json en base64 pour Railway."""
from __future__ import annotations

import base64
from pathlib import Path


def encode(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        print(f"⚠️  {path} introuvable")
        return None
    enc = base64.b64encode(p.read_bytes()).decode()
    return enc


def main():
    print("== Variables d'environnement à ajouter dans Railway ==\n")
    tok = encode("token.json")
    if tok:
        print("GOOGLE_TOKEN_JSON=")
        print(tok)
        print()
    cred = encode("credentials.json")
    if cred:
        print("GOOGLE_CREDENTIALS_JSON=")
        print(cred)


if __name__ == "__main__":
    main()
