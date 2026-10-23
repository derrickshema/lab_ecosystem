"""
Generate the RS256 key pair Identity uses to sign tokens.

    python -m scripts.generate_jwt_keys          # refuses to overwrite
    python -m scripts.generate_jwt_keys --force  # rotate: replaces both keys

The private key must stay secret (keys/ is gitignored and excluded from
Docker images). After rotating, change JWT_KEY_ID so verifiers can tell the
keys apart, and expect existing tokens to stop verifying.
"""

import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import settings


def main() -> None:
    private_path = Path(settings.JWT_PRIVATE_KEY_PATH)
    public_path = Path(settings.JWT_PUBLIC_KEY_PATH)

    if private_path.exists() and "--force" not in sys.argv:
        sys.exit(f"{private_path} already exists. Use --force to replace it.")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    public_path.write_bytes(key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    print(f"Wrote {private_path} (secret) and {public_path}")


if __name__ == "__main__":
    main()
