from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class FFprobeError(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioInfo:
    path: Path
    duration_s: float
    sample_rate: Optional[int]
    channels: Optional[int]
    codec: Optional[str]
    bit_rate: Optional[int]


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise FFprobeError(p.stderr.strip() or "ffprobe failed")
    return p.stdout


def probe_file(path: Path) -> AudioInfo:
    path = Path(path)
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    raw = _run(cmd)
    data = json.loads(raw)

    duration = None
    fmt = data.get("format") or {}
    if "duration" in fmt:
        try:
            duration = float(fmt["duration"])
        except Exception:
            duration = None
    if duration is None:
        raise FFprobeError("Could not determine duration")

    bit_rate = None
    if "bit_rate" in fmt:
        try:
            bit_rate = int(fmt["bit_rate"])
        except Exception:
            bit_rate = None

    sr = None
    ch = None
    codec = None
    for s in data.get("streams", []):
        if s.get("codec_type") == "audio":
            codec = s.get("codec_name")
            if "sample_rate" in s:
                try:
                    sr = int(s["sample_rate"])
                except Exception:
                    sr = None
            if "channels" in s:
                try:
                    ch = int(s["channels"])
                except Exception:
                    ch = None
            break

    return AudioInfo(
        path=path,
        duration_s=duration,
        sample_rate=sr,
        channels=ch,
        codec=codec,
        bit_rate=bit_rate,
    )


def probe_files(paths: list[Path]) -> list[AudioInfo]:
    out: list[AudioInfo] = []
    for p in paths:
        out.append(probe_file(p))
    return out