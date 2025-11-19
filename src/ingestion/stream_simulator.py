# src/ingestion/stream_simulator.py
import time
from typing import Iterator, Optional

import pandas as pd

from src.config import PROCESSED_DATA_PATH, REALISTIC_STREAM_PATH, SYNTHETIC_STREAM_PATH, STREAM_SLEEP_SECONDS


class StreamSimulator:
    """
    Simple CSV-based streaming simulator.
    Yields row-by-row dicts at a fixed rate.

    Default: Uses REALISTIC_STREAM_PATH (sorted by tool wear) for realistic degradation simulation.
    Fallback: PROCESSED_DATA_PATH (shuffled) if realistic version doesn't exist.
    """

    def __init__(
        self,
        path: Optional[str] = None,
        sleep_seconds: float = STREAM_SLEEP_SECONDS,
        loop_forever: bool = False,
    ):
        # Priority: custom path > realistic stream > synthetic > processed (shuffled)
        if path:
            self.path = path
        elif REALISTIC_STREAM_PATH.exists():
            self.path = str(REALISTIC_STREAM_PATH)
        elif SYNTHETIC_STREAM_PATH.exists():
            self.path = str(SYNTHETIC_STREAM_PATH)
        else:
            self.path = str(PROCESSED_DATA_PATH)
        self.sleep_seconds = sleep_seconds
        self.loop_forever = loop_forever
        self.df = pd.read_csv(self.path)

    def __iter__(self) -> Iterator[pd.Series]:
        while True:
            for _, row in self.df.iterrows():
                yield row
                if self.sleep_seconds > 0:
                    time.sleep(self.sleep_seconds)
            if not self.loop_forever:
                break
