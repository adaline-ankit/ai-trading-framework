from __future__ import annotations

import os
from abc import ABC, abstractmethod


class SecretStore(ABC):
    @abstractmethod
    def get_secret(self, key: str) -> str | None: ...


class EnvSecretStore(SecretStore):
    def get_secret(self, key: str) -> str | None:
        return os.getenv(key)
