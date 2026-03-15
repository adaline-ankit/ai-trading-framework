from __future__ import annotations

import hashlib
import hmac


class SignatureVerifier:
    def __init__(self, secret: str) -> None:
        self.secret = secret.encode("utf-8")

    def sign(self, payload: bytes) -> str:
        return hmac.new(self.secret, payload, hashlib.sha256).hexdigest()

    def verify(self, payload: bytes, signature: str) -> bool:
        expected = self.sign(payload)
        return hmac.compare_digest(expected, signature)
