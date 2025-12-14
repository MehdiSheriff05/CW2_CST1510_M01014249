# dataset domain model

from __future__ import annotations


class Dataset:
    # represents a managed dataset

    def __init__(self, **kwargs):
        # keep the original record handy
        self.data = kwargs

    def calculate_size_mb(self) -> float:
        # return the file size stored on the record
        # guard against missing or invalid size values
        try:
            return float(self.data.get("size_mb", 0.0))
        except (TypeError, ValueError):
            return 0.0

    def __str__(self) -> str:  # pragma: no cover - debug helper
        # quick representation used for debugging only
        name = self.data.get("name", "unknown")
        size = self.calculate_size_mb()
        return f"Dataset(name={name}, size_mb={size})"
