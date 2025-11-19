# src/storage/buffer.py
from collections import deque
from typing import Any, Deque, Dict, List, Optional


class InMemoryBuffer:
    """
    Very simple in-memory circular buffer for recent datapoints and model outputs.
    """

    def __init__(self, maxlen: int = 500):
        self._data: Deque[Dict[str, Any]] = deque(maxlen=maxlen)

    def append(self, item: Dict[str, Any]) -> None:
        self._data.append(item)

    def latest(self, n: int = 1) -> List[Dict[str, Any]]:
        if n <= 0:
            return []
        return list(self._data)[-n:]

    def all(self) -> List[Dict[str, Any]]:
        return list(self._data)

    def __len__(self) -> int:
        return len(self._data)
