from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class FFmpegError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConvertOptions:
    out_dir: Path
    sample_rate: int = 48000
    channels: int = 1
    bit_depth: int = 16
    overwrite: bool = False
    force_wav: bool = True


def _pcm_codec(bit_depth: int) -> str:
    m = {16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_s32le"}
    if bit_depth not in m:
        raise ValueError("bit_depth must be one of 16, 24, 32")
    return m[bit_depth]


def convert_file(in_path: Path, opts: ConvertOptions) -> Path:
    in_path = Path(in_path)
    opts.out_dir.mkdir(parents=True, exist_ok=True)

    out_ext = ".wav" if opts.force_wav else in_path.suffix
    out_path = opts.out_dir / f"{in_path.stem}{out_ext}"

    cmd = ["ffmpeg"]
    cmd += ["-y" if opts.overwrite else "-n"]
    cmd += ["-i", str(in_path), "-vn", "-ac", str(opts.channels), "-ar", str(opts.sample_rate)]

    if out_ext.lower() == ".wav":
        cmd += ["-c:a", _pcm_codec(opts.bit_depth)]
    else:
        cmd += ["-c:a", "copy"]

    cmd += [str(out_path)]

    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise FFmpegError(p.stderr.strip() or "ffmpeg failed")
    return out_path


def convert_files(paths: list[Path], opts: ConvertOptions) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        out.append(convert_file(p, opts))
    return out