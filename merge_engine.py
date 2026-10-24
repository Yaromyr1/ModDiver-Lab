"""Safer byte-level merge helpers for ModDiver Laboratory.

This module deliberately does not pretend to understand undocumented game schemas.
It merges byte edits relative to a known stock baseline, reports collisions, and
fails closed when input lengths make offset-based merging unsafe.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


class MergeSafetyError(ValueError):
    """Raised when a binary merge cannot be performed safely."""


@dataclass(frozen=True)
class ByteRun:
    start: int
    end: int  # inclusive

    def overlaps(self, other: "ByteRun") -> bool:
        return self.start <= other.end and other.start <= self.end


@dataclass(frozen=True)
class Conflict:
    start: int
    end: int
    earlier_mod: str
    later_mod: str


def diff_runs(stock: bytes, candidate: bytes) -> list[ByteRun] | None:
    """Return contiguous changed byte ranges; None means file lengths differ."""
    if len(stock) != len(candidate):
        return None
    runs: list[ByteRun] = []
    start = None
    for i, (a, b) in enumerate(zip(stock, candidate)):
        if a != b:
            if start is None:
                start = i
        elif start is not None:
            runs.append(ByteRun(start, i - 1))
            start = None
    if start is not None:
        runs.append(ByteRun(start, len(stock) - 1))
    return runs


def plan_merge(stock: bytes, mods: Sequence[tuple[str, bytes]], row_size: int = 0) -> tuple[bytes, list[Conflict]]:
    """Apply mods in order; later mods win overlapping bytes, with explicit conflicts.

    ``row_size`` enables field-aware reporting: two mods that change *different bytes*
    of the same fixed-size row (e.g. two fields of one weapon) are still a conflict,
    because a byte splice can leave a row the game does not expect.
    """
    output = bytearray(stock)
    # Track ownership as intervals rather than one Python object per byte. Game
    # resources can be large, and a per-byte owner array can consume many times
    # the size of the resource in RAM.
    owners: list[tuple[int, int, str]] = []
    conflicts: list[Conflict] = []
    for name, candidate in mods:
        runs = diff_runs(stock, candidate)
        if runs is None:
            raise MergeSafetyError(
                f"{name}: file length {len(candidate)} differs from stock length {len(stock)}"
            )
        for run in runs:
            for left, right, owner in owners:
                if row_size > 0 and (left // row_size) == (run.start // row_size):
                    rs = (left // row_size) * row_size
                    s, e = rs, min(rs + row_size - 1, len(stock) - 1)
                    if any(output[i] != candidate[i] for i in range(s, e + 1)):
                        conflicts.append(Conflict(s, e, owner, name))
                    else:
                        conflicts.append(Conflict(s, e, owner + " (same row)", name))
                if right < run.start:
                    continue
                if left > run.end:
                    break
                s, e = max(left, run.start), min(right, run.end)
                if any(output[i] != candidate[i] for i in range(s, e + 1)):
                    conflicts.append(Conflict(s, e, owner, name))
            output[run.start:run.end + 1] = candidate[run.start:run.end + 1]
            updated = []
            for left, right, owner in owners:
                if right < run.start or left > run.end:
                    updated.append((left, right, owner))
                    continue
                if left < run.start:
                    updated.append((left, run.start - 1, owner))
                if right > run.end:
                    updated.append((run.end + 1, right, owner))
            updated.append((run.start, run.end, name))
            updated.sort(key=lambda item: item[0])
            # Coalesce adjacent intervals with identical ownership.
            owners = []
            for item in updated:
                if owners and owners[-1][2] == item[2] and owners[-1][1] + 1 == item[0]:
                    prev = owners[-1]
                    owners[-1] = (prev[0], item[1], prev[2])
                else:
                    owners.append(item)
    return bytes(output), conflicts


def atomic_write(path: str | Path, data: bytes) -> None:
    """Write beside the destination and atomically replace it after a full flush."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{dest.name}.", suffix=".tmp", dir=str(dest.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, dest)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def validate_sealed_input(data: bytes, label: str = "input") -> None:
    """Basic envelope validation before crypto open; sealed-box overhead is 48 bytes."""
    if not isinstance(data, bytes):
        raise TypeError(f"{label} must be bytes")
    if len(data) < 48:
        raise MergeSafetyError(f"{label} is truncated: {len(data)} bytes; minimum sealed envelope is 48")
