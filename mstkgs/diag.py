# -*- coding: utf-8 -*-
import io
import os
import platform
import sys
import time

from .compat import uni
from .conf import NAME, VERSION, opts

LIMIT = 512 * 1024
CANDIDATES = ("/home/root/logs", "/media/hdd/logs", "/tmp")
INFO_FILES = (
    ("Model", ("/proc/stb/info/vumodel", "/proc/stb/info/model", "/proc/stb/info/boxtype", "/proc/stb/info/gbmodel",
               "/etc/model")),
    ("Marka", ("/proc/stb/info/brand", "/etc/brand")),
    ("Imaj", ("/etc/image-version", "/etc/issue.net", "/etc/issue")),
    ("Dagitim", ("/etc/os-release",)),
)


def where():
    for folder in CANDIDATES:
        if os.path.isdir(folder) and os.access(folder, os.W_OK):
            return os.path.join(folder, "mstkgs_tani.log")
    return "/tmp/mstkgs_tani.log"


def _peek(paths, limit=6):
    for path in paths:
        try:
            with io.open(path, "r", encoding="utf-8", errors="replace") as handle:
                rows = [r.strip() for r in handle.read().splitlines() if r.strip()]
            if rows:
                return u" | ".join(rows[:limit])
        except (IOError, OSError):
            continue
    return u"-"


def _cpu():
    picked = []
    try:
        with io.open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as handle:
            for row in handle.read().splitlines():
                head = row.split(":", 1)[0].strip().lower()
                if head in ("model name", "hardware", "cpu model", "system type", "processor") and ":" in row:
                    value = row.split(":", 1)[1].strip()
                    if value and not value.isdigit() and value not in picked:
                        picked.append(value)
    except (IOError, OSError):
        pass
    return u", ".join(uni(v) for v in picked[:3]) or u"-"


class Journal(object):
    opened = False

    @staticmethod
    def active():
        try:
            return bool(opts.diag.value)
        except Exception:
            return False

    @classmethod
    def path(cls):
        return where()

    @classmethod
    def _append(cls, text):
        target = where()
        try:
            if os.path.exists(target) and os.path.getsize(target) > LIMIT:
                with io.open(target, "r", encoding="utf-8", errors="replace") as handle:
                    tail = handle.read()[-LIMIT // 2:]
                with io.open(target, "w", encoding="utf-8") as handle:
                    handle.write(u"... (eski kayitlar kirpildi)\n" + tail)
            with io.open(target, "a", encoding="utf-8") as handle:
                handle.write(uni(text))
        except (IOError, OSError):
            pass

    @classmethod
    def note(cls, topic, *details, **fields):
        if not cls.active():
            return
        if not cls.opened:
            cls.opened = True
            cls.snapshot()
        parts = [uni(d) for d in details]
        parts += [u"%s=%s" % (k, uni(v)) for k, v in sorted(fields.items())]
        cls._append(u"%s [%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), uni(topic), u"  ".join(parts)))

    @classmethod
    def snapshot(cls):
        rows = [u"", u"=" * 72, u"%s v%s  tani kaydi  %s" % (uni(NAME), uni(VERSION), time.strftime("%Y-%m-%d %H:%M:%S"))]
        for label, paths in INFO_FILES:
            rows.append(u"%-10s %s" % (label, _peek(paths, 4 if label == "Dagitim" else 2)))
        rows.append(u"%-10s %s" % ("Islemci", _cpu()))
        rows.append(u"%-10s %s / cekirdek %s" % ("Mimari", uni(platform.machine()), uni(platform.release())))
        rows.append(u"%-10s %s" % ("Python", uni(sys.version.split()[0])))
        rows += cls._enigma() + cls._tuners() + cls._demux()
        rows.append(u"=" * 72)
        cls._append(u"\n".join(rows) + u"\n")

    @staticmethod
    def _enigma():
        rows = []
        try:
            from enigma import getDesktop
            size = getDesktop(0).size()
            rows.append(u"%-10s %dx%d" % ("Ekran", size.width(), size.height()))
        except Exception:
            rows.append(u"%-10s -" % "Ekran")
        try:
            from Components.config import config
            rows.append(u"%-10s %s" % ("Skin", uni(config.skin.primary_skin.value)))
        except Exception:
            pass
        try:
            from Components.About import about
            rows.append(u"%-10s %s" % ("Enigma2", uni(about.getEnigmaVersionString())))
        except Exception:
            pass
        return rows

    @staticmethod
    def _tuners():
        rows = []
        try:
            from Components.NimManager import nimmanager
            for unit in nimmanager.nim_slots:
                try:
                    sats = [s[0] for s in nimmanager.getSatListForNim(unit.slot)] if unit.isCompatible("DVB-S") else []
                except Exception:
                    sats = []
                fbc = bool(getattr(unit, "isFBCLink", lambda: False)())
                rows.append(u"Tuner %s   %s  %s  uydu=%s%s" % (
                    chr(65 + unit.slot), uni(getattr(unit, "description", "?")),
                    uni(unit.getType() if hasattr(unit, "getType") else "?"),
                    u",".join(str(s) for s in sats) or u"-", u"  FBC-link" if fbc else u""))
        except Exception as exc:
            rows.append(u"Tuner listesi alinamadi: %s" % uni(exc))
        return rows

    @staticmethod
    def _demux():
        try:
            from .dvb import Ioctl
            codes = Ioctl()
            nodes = sorted(os.listdir("/dev/dvb/adapter0")) if os.path.isdir("/dev/dvb/adapter0") else []
            return [u"%-10s %s" % ("DVB", u" ".join(uni(n) for n in nodes) or u"-"),
                    u"%-10s filtre=0x%08X dur=0x%08X tampon=0x%08X (%s)" % (
                        "ioctl", codes.filter, codes.stop, codes.buffer, u"mips" if codes.size_bits == 13 else u"standart")]
        except Exception as exc:
            return [u"DVB bilgisi alinamadi: %s" % uni(exc)]


def note(topic, *details, **fields):
    try:
        Journal.note(topic, *details, **fields)
    except Exception:
        pass
