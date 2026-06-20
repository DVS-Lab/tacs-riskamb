"""Optional LSL synchronization with unconditional local marker logging."""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

try:  # Optional by design.
    import pylsl  # type: ignore
except ImportError:  # pragma: no cover - tested by module reload
    pylsl = None


class MarkerLogger:
    """Log every marker locally and optionally publish it through LSL."""

    def __init__(self, path: Path, trigger_config: Mapping[str, Any]) -> None:
        self.path = Path(path)
        self.marker_map = dict(trigger_config["marker_map"])
        self.outlet = None
        if trigger_config.get("lsl_enabled") and pylsl is not None:
            try:
                info = pylsl.StreamInfo(
                    trigger_config.get("lsl_stream_name", "RiskAmbiguityMarkers"),
                    "Markers", 1, 0, "int32", "riskambiguity-marker-source",
                )
                self.outlet = pylsl.StreamOutlet(info)
            except Exception:
                self.outlet = None
        self._stream = self.path.open("x", encoding="utf-8", newline="", buffering=1)
        self._fields = ["marker_label", "marker_code", "local_perf_counter", "lsl_timestamp", "payload"]
        self._writer = csv.DictWriter(self._stream, fieldnames=self._fields)
        self._writer.writeheader()
        self._sync()

    @property
    def lsl_active(self) -> bool:
        return self.outlet is not None

    def _sync(self) -> None:
        self._stream.flush()
        os.fsync(self._stream.fileno())

    def send(self, label: str, payload: str = "") -> float:
        code = int(self.marker_map[label])
        local_time = time.perf_counter()
        lsl_time: Optional[float] = None
        if self.outlet is not None:
            try:
                lsl_time = float(pylsl.local_clock())
                self.outlet.push_sample([code], lsl_time)
            except Exception:
                self.outlet = None
        self._writer.writerow(
            {
                "marker_label": label,
                "marker_code": code,
                "local_perf_counter": f"{local_time:.9f}",
                "lsl_timestamp": "" if lsl_time is None else f"{lsl_time:.9f}",
                "payload": payload,
            }
        )
        self._sync()
        return local_time

    def close(self) -> None:
        if not self._stream.closed:
            self._sync()
            self._stream.close()


class LSLStartListener:
    """Nonblocking listener for a configured scanner/laboratory start marker."""

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.inlet = None
        self.target = int(config.get("lsl_start_marker", 203))
        if not config.get("lsl_enabled") or pylsl is None:
            return
        try:
            streams = pylsl.resolve_byprop("type", "Markers", timeout=0.1)
            if streams:
                self.inlet = pylsl.StreamInlet(streams[0])
        except Exception:
            self.inlet = None

    def poll(self) -> bool:
        if self.inlet is None:
            return False
        try:
            sample, _ = self.inlet.pull_sample(timeout=0.0)
            return bool(sample and int(sample[0]) == self.target)
        except Exception:
            return False

