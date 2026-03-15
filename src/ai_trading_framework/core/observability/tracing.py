from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def traced(name: str) -> Iterator[dict[str, str]]:
    yield {"span": name}
