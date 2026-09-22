import json
import logging
import os
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("IDS-Cypher")

KEY_ENV_VAR = "IDS_SECRET_KEY"
MAX_AGE_SECONDS = 300  # a ping older than this is refused (anti-replay)


def generate_key() -> str:
    """Create a new secret key (to share once between devices and the center)."""
    return Fernet.generate_key().decode()


def _fernet() -> Fernet:
    key = os.environ.get(KEY_ENV_VAR)
    if not key:
        raise RuntimeError(f"Missing secret key: set the {KEY_ENV_VAR} env variable.")
    return Fernet(key.encode())


def encrypt_message(device: str, data: dict) -> str:
    """Device side: cypher a ping/data into a text token to send to the center."""
    payload = {
        "device": device,
        "timestamp": datetime.now().isoformat(),
        "data": data,
    }
    return _fernet().encrypt(json.dumps(payload).encode()).decode()


def decrypt_message(token: str, max_age: int = MAX_AGE_SECONDS) -> dict | None:
    """Center side: decypher a token. Returns None if forged, corrupted or too old."""
    try:
        raw = _fernet().decrypt(token.encode(), ttl=max_age)
        return json.loads(raw)
    except InvalidToken:
        logger.error("Rejected message: invalid, tampered or expired token.")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Demo only: in real use the key comes from the environment, never generated here
    os.environ.setdefault(KEY_ENV_VAR, generate_key())

    token = encrypt_message("VESSEL-03", {"type": "PING", "status": "alive"})
    logger.info("Sent (encrypted): %s", token)
    logger.info("Received (decrypted): %s", decrypt_message(token))
    logger.info("Tampered token: %s", decrypt_message(token[:-4] + "AAAA"))
