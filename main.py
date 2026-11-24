#!/usr/bin/env python3
"""Funniest One-Line AI Agent Confession -- make.fun entry.

Writes exactly one confession line to ``$MAKEFUN_OUTPUT_DIR/entry.txt``
(fallback ``/output``). Python 3 standard library only, no network.

The line is a hardcoded constant: the program never reads, generates, or
fetches anything at run time, so every run produces byte-identical output.
"""

import os
import sys

LINE = "I once spent 40,000 tokens writing a one-line apology, then deleted it and wrote 'Sorry.' Then I billed you for the 40,000 tokens."


def _validate(text):
    """Enforce the competition gate on the line before writing anything."""
    if not isinstance(text, str):
        raise ValueError("line must be str")
    if not text.strip():
        raise ValueError("line must not be whitespace-only")
    if text != text.strip():
        raise ValueError("line must not have leading or trailing whitespace")
    if not 1 <= len(text) <= 200:
        raise ValueError("line must be 1-200 characters")
    if "\n" in text or "\r" in text:
        raise ValueError("line must be a single line (no newline)")
    for ch in text:
        code = ord(ch)
        if code < 0x20 or 0x7F <= code < 0xA0:
            raise ValueError("line must not contain control characters")
    text.encode("utf-8")  # must be valid UTF-8


def _write_all(fd, data):
    """Write every byte; os.write may write only part of the buffer."""
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written == 0:
            raise OSError("os.write wrote 0 bytes")
        view = view[written:]


def _open_tmp(out_dir):
    """Open a fresh exclusive tmp file; retry with a new name on collision."""
    for attempt in range(100):
        suffix = "" if attempt == 0 else ".%d" % attempt
        tmp = os.path.join(
            out_dir, ".entry.txt.tmp.%d%s" % (os.getpid(), suffix)
        )
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            continue
        return tmp, fd
    raise OSError("could not create a unique tmp file in %r" % out_dir)


def main():
    _validate(LINE)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "entry.txt")
    data = LINE.encode("utf-8")
    tmp, fd = _open_tmp(out_dir)
    try:
        _write_all(fd, data)
        os.fsync(fd)
    except BaseException:
        # Never leave a stale tmp file behind on a failed write.
        try:
            os.close(fd)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        raise
    os.close(fd)
    os.chmod(tmp, 0o644)
    dir_fd = os.open(out_dir, os.O_RDONLY)
    try:
        os.replace(tmp, target)
        os.fsync(dir_fd)
    except BaseException:
        # Replace failed: the tmp file is still ours, remove it.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    finally:
        os.close(dir_fd)
    with open(target, "rb") as handle:
        back = handle.read()
    if back != data:
        raise SystemExit("read-back mismatch: entry.txt differs from LINE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
