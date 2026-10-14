import io
import os
import sys
import time

PY2 = sys.version_info[0] == 2

try:
    TEXT = unicode
except NameError:
    TEXT = str

clock = getattr(time, "monotonic", time.time)
swap = getattr(os, "replace", os.rename)


def uni(value):
    if isinstance(value, TEXT):
        return value
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "replace")
    return TEXT(value)


def native(value):
    if value is None:
        return ""
    if PY2:
        if isinstance(value, TEXT):
            return value.encode("utf-8")
        return value if isinstance(value, str) else str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value if isinstance(value, str) else str(value)


def slurp(path):
    with io.open(path, "r", encoding="utf-8", errors="replace") as handle:
        return uni(handle.read())


def dump(path, text):
    temp = path + ".tmp"
    with io.open(temp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(uni(text))
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    swap(temp, path)


def clone(src, dst):
    with open(src, "rb") as handle:
        data = handle.read()
    temp = dst + ".tmp"
    with open(temp, "wb") as handle:
        handle.write(data)
    swap(temp, dst)
