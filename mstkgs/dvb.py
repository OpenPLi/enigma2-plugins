# -*- coding: utf-8 -*-
import errno
import fcntl
import os
import platform
import select
import struct
import threading

from .compat import clock

PID = 0x1FF5
TABLE = 0xA7


class Crc(object):
    POLY = 0x04C11DB7
    _table = None

    @classmethod
    def table(cls):
        if cls._table is None:
            rows = []
            for byte in range(256):
                acc = byte << 24
                for _bit in range(8):
                    acc = ((acc << 1) ^ cls.POLY) if acc & 0x80000000 else (acc << 1)
                    acc &= 0xFFFFFFFF
                rows.append(acc)
            cls._table = tuple(rows)
        return cls._table

    @classmethod
    def residue(cls, data):
        rows = cls.table()
        acc = 0xFFFFFFFF
        for byte in bytearray(data):
            acc = ((acc << 8) & 0xFFFFFFFF) ^ rows[(acc >> 24) ^ byte]
        return acc

    @classmethod
    def valid(cls, data):
        return cls.residue(data) == 0


class Packet(object):
    __slots__ = ("blob", "ext_id", "rev", "seq", "last_seq", "sound")

    def __init__(self, blob, ext_id, rev, seq, last_seq, sound):
        self.blob, self.ext_id, self.rev, self.seq, self.last_seq, self.sound = blob, ext_id, rev, seq, last_seq, sound

    @property
    def body(self):
        return self.blob[8:len(self.blob) - 4]

    @property
    def slot(self):
        return (self.ext_id, self.rev, self.last_seq)

    @classmethod
    def decode(cls, data, verify=True):
        buf = bytearray(data)
        if len(buf) < 0x0C or buf[0] != TABLE or (buf[1] & 0x80) == 0:
            return None
        declared = 3 + ((buf[1] & 0x0F) << 8 | buf[2])
        if len(buf) == declared - 4:
            buf.extend(b"\0\0\0\0")
        if len(buf) != declared:
            return None
        if (buf[5] & 1) == 0 or buf[6] > buf[7]:
            return None
        sound = Crc.valid(buf)
        if verify and not sound:
            return None
        return cls(bytes(buf), buf[3] << 8 | buf[4], buf[5] >> 1 & 0x1F, buf[6], buf[7], sound)


class Splitter(object):
    LIMIT = 65536

    def __init__(self):
        self.pending = bytearray()

    def clear(self):
        del self.pending[:]

    def push(self, chunk):
        buf = self.pending
        buf.extend(chunk)
        found = []
        cursor = 0
        while len(buf) - cursor >= 3:
            if buf[cursor] != TABLE or not buf[cursor + 1] & 0x80:
                cursor += 1
                continue
            size = 3 + (((buf[cursor + 1] & 0x0F) << 8) | buf[cursor + 2])
            if size < 0x0C:
                cursor += 1
                continue
            if len(buf) - cursor < size:
                break
            found.append(bytes(buf[cursor:cursor + size]))
            cursor += size
        del buf[:cursor]
        if len(buf) > self.LIMIT:
            self.clear()
        return found


class TsJoiner(object):
    SIZE = 188

    def __init__(self, pid=PID):
        self.pid = pid
        self.raw = bytearray()
        self.part = None
        self.cc = None
        self.packets = 0
        self.breaks = 0

    def clear(self):
        del self.raw[:]
        self.part = None
        self.cc = None

    def _harvest(self, out):
        part = self.part
        while part is not None and len(part) >= 3:
            if part[0] == 0xFF:
                part = None
                break
            size = 3 + ((part[1] & 0x0F) << 8 | part[2])
            if len(part) < size:
                break
            if part[0] == TABLE:
                out.append(bytes(part[:size]))
            part = part[size:]
        self.part = part if part else None

    def _packet(self, pkt, out):
        if (pkt[1] & 0x1F) << 8 | pkt[2] != self.pid:
            return
        self.packets += 1
        if pkt[1] & 0x80:
            self.part = None
            return
        control = pkt[3] >> 4 & 3
        counter = pkt[3] & 0x0F
        if control in (0, 2):
            return
        start = 4
        if control == 3:
            start += 1 + pkt[4]
        if start >= self.SIZE:
            return
        if self.cc is not None:
            if counter == self.cc:
                return
            if counter != (self.cc + 1) % 16:
                self.breaks += 1
                self.part = None
        self.cc = counter
        body = pkt[start:]
        if pkt[1] & 0x40:
            pointer = body[0]
            body = body[1:]
            if self.part is not None:
                self.part.extend(body[:pointer])
                self._harvest(out)
            self.part = bytearray(body[pointer:])
        elif self.part is None:
            return
        else:
            self.part.extend(body)
        self._harvest(out)

    def push(self, chunk):
        buf = self.raw
        buf.extend(chunk)
        out = []
        cursor = 0
        size = self.SIZE
        while len(buf) - cursor >= size:
            if buf[cursor] != 0x47:
                cursor += 1
                continue
            self._packet(buf[cursor:cursor + size], out)
            cursor += size
        del buf[:cursor]
        return out


class Assembler(object):
    QUORUM = 2

    def __init__(self, verify=True):
        self.verify = verify
        self.parts = {}
        self.doubtful = {}
        self.dropped = 0
        self.repeats = 0
        self.suspect = 0
        self.fresh_at = 0.0
        self.grew_at = 0.0

    def _entry(self, pkt):
        entry = self.parts.get(pkt.ext_id)
        if entry is None:
            entry = self.parts[pkt.ext_id] = [pkt.rev, pkt.last_seq, {}]
            self.fresh_at = clock()
        elif entry[0] != pkt.rev:
            if (pkt.rev - entry[0]) % 32 >= 16:
                return None
            entry[:] = [pkt.rev, pkt.last_seq, {}]
            self.doubtful = {}
        elif entry[1] != pkt.last_seq:
            return None
        return entry

    def _store(self, entry, pkt):
        if pkt.seq in entry[2]:
            self.repeats += 1
            return False
        entry[2][pkt.seq] = pkt.blob
        self.grew_at = clock()
        return True

    def offer(self, data):
        pkt = Packet.decode(data, False)
        if pkt is None:
            self.dropped += 1
            return False
        if pkt.sound:
            entry = self._entry(pkt)
            if entry is None:
                self.dropped += 1
                return False
            stored = self._store(entry, pkt)
            self._settle()
            return stored
        self.suspect += 1
        key = pkt.slot + (pkt.seq,)
        votes = self.doubtful.setdefault(key, {})
        votes[pkt.blob] = votes.get(pkt.blob, 0) + 1
        return False if self.verify else self._settle()

    def _settle(self):
        placed = False
        for key, votes in list(self.doubtful.items()):
            ext_id, rev, last_seq, seq = key
            blob, count = max(votes.items(), key=lambda item: item[1])
            entry = self.parts.get(ext_id)
            if entry is not None and seq in entry[2]:
                continue
            if entry is None and not self.parts:
                if count < self.QUORUM:
                    continue
            elif entry is None or entry[0] != rev or entry[1] != last_seq or count < self.QUORUM:
                continue
            pkt = Packet(blob, ext_id, rev, seq, last_seq, False)
            target = self._entry(pkt)
            if target is not None and self._store(target, pkt):
                placed = True
        return placed

    def progress(self):
        return (sum(len(s[2]) for s in self.parts.values()),
                sum(s[1] + 1 for s in self.parts.values()))

    def done(self):
        return bool(self.parts) and all(len(s[2]) == s[1] + 1 for s in self.parts.values())

    def sound(self):
        return all(Crc.valid(b) for b in self.ordered())

    def ordered(self):
        out = []
        for ext in sorted(self.parts):
            chunks = self.parts[ext][2]
            out.extend(chunks[i] for i in sorted(chunks))
        return out

    def missing(self):
        out = []
        for ext in sorted(self.parts):
            rev, last, chunks = self.parts[ext]
            out.extend("%d/%d" % (ext, i) for i in range(last + 1) if i not in chunks)
        return out

    def revisions(self):
        return dict((ext, s[0]) for ext, s in self.parts.items())


def stitch(blobs, verify=True):
    ordered = sorted((p.ext_id, p.seq, p.body) for p in (Packet.decode(b, False) for b in blobs)
                     if p is not None and (p.sound or not verify))
    return b"".join(chunk for _, _, chunk in ordered)


def save(path, raws):
    with open(path, "wb") as handle:
        for raw in raws:
            handle.write(raw)


def restore_blobs(path):
    with open(path, "rb") as handle:
        return Splitter().push(handle.read())


class Ioctl(object):
    LAYOUT = struct.Struct("=H16s16s16s2xII")
    CHECK_CRC = 1
    IMMEDIATE = 4

    def __init__(self, machine=None):
        arch = (machine or platform.machine()).lower()
        legacy = arch.startswith(("mips", "ppc", "powerpc", "sparc", "parisc", "alpha"))
        self.size_bits = 13 if legacy else 14
        self.none_dir = 1 if legacy else 0
        self.write_dir = 4 if legacy else 1
        self.granted = 0
        self.start = self.code(41)
        self.stop = self.code(42)
        self.filter = self.code(43, self.LAYOUT.size, True)
        self.buffer = self.code(45)

    def code(self, nr, size=0, write=False):
        direction = self.write_dir if write else self.none_dir
        return (direction << (16 + self.size_bits)) | (size << 16) | (ord("o") << 8) | nr

    PES_LAYOUT = struct.Struct("=H2xIIII")

    def pes(self, port, pid=PID):
        try:
            self.call(port, self.stop)
        except (OSError, IOError):
            pass
        self.call(port, self.code(44, self.PES_LAYOUT.size, True), self.PES_LAYOUT.pack(pid, 0, 3, 20, self.IMMEDIATE))

    def params(self, verify):
        flags = self.IMMEDIATE | (self.CHECK_CRC if verify else 0)
        return self.LAYOUT.pack(PID, struct.pack("B", TABLE), b"\xff", b"", 0, flags)

    @staticmethod
    def call(port, request, arg=0):
        try:
            return fcntl.ioctl(port, request, arg)
        except OverflowError:
            return fcntl.ioctl(port, request - (1 << 32) if request >= (1 << 31) else request, arg)

    def arm(self, port, verify=False):
        try:
            self.call(port, self.stop)
        except (OSError, IOError):
            pass
        for size in (1024 * 1024, 512 * 1024, 256 * 1024, 128 * 1024):
            try:
                self.call(port, self.buffer, size)
                self.granted = size
                break
            except (OSError, IOError, TypeError):
                continue
        self.call(port, self.filter, self.params(verify))

    def disarm(self, port):
        try:
            self.call(port, self.stop)
        except (OSError, IOError, TypeError):
            pass


def demuxes(adapter=0, first=None):
    root = "/dev/dvb/adapter%d" % adapter
    paths = ["%s/demux%d" % (root, first)] if first is not None else []
    try:
        names = sorted(n for n in os.listdir(root) if n.startswith("demux"))
    except OSError:
        names = []
    for name in names:
        path = os.path.join(root, name)
        if path not in paths:
            paths.append(path)
    return paths


def _open(path):
    try:
        return os.open(path, os.O_RDWR | os.O_NONBLOCK)
    except OSError:
        return os.open(path, os.O_RDONLY | os.O_NONBLOCK)


class Grabber(threading.Thread):
    def __init__(self, paths, limit=60.0, idle=20.0, relax=25.0, calm=2.0, opener=None, arm=None, switch=12.0):
        threading.Thread.__init__(self, name="MSTKGSGrabber")
        self.daemon = True
        self.paths = list(paths)
        self.limit = limit
        self.idle = idle
        self.relax = relax
        self.calm = calm
        self.opener = opener or _open
        self.ioctl = Ioctl()
        self.arm = arm or self.ioctl.arm
        self.halt = threading.Event()
        self.table = Assembler(True)
        self.verified = True
        self.fault = None
        self.over = False
        self.whole = False
        self.spent = 0.0
        self.source = None
        self.count = 0
        self.trail = []
        self.overflows = 0
        self.reads = 0
        self.odd_reads = 0
        self.stripped = 0
        self.switch = switch
        self.mode = "section"

    def abort(self):
        self.halt.set()

    def snapshot(self):
        have, total = self.table.progress()
        return {"have": have, "total": total, "elapsed": self.spent, "crc": self.table.verify, "mode": self.mode,
                "count": self.count, "tables": len(self.table.parts)}

    def _attach(self):
        handles = {}
        for path in self.paths:
            try:
                port = self.opener(path)
            except (OSError, IOError) as exc:
                self.trail.append("acilamadi %s: %s" % (path, exc))
                continue
            try:
                self.arm(port, False)
            except (OSError, IOError) as exc:
                self.trail.append("filtre kurulamadi %s: %s" % (path, exc))
                os.close(port)
                continue
            self.trail.append("dinleniyor %s (tampon %d KB)" % (path, self.ioctl.granted // 1024))
            handles[port] = [path, Splitter()]
        return handles

    def _relax(self, handles):
        self.table.verify = False
        self.trail.append("CRC hatali bolumler oylamaya alindi (%.1f sn, %d/%d bolum, %d supheli)"
                          % ((self.spent,) + self.table.progress() + (self.table.suspect,)))
        self.table._settle()

    def _drain(self, port, entry):
        for _round in range(0x20):
            try:
                piece = os.read(port, 0x2000 if self.mode == "section" else 188 * 256)
            except (OSError, IOError) as exc:
                if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR):
                    return
                if exc.errno == errno.EOVERFLOW:
                    self.overflows += 1
                    entry[1].clear()
                    continue
                raise
            if not piece:
                return
            self.reads += 1
            whole = self._single(piece) if self.mode == "section" else None
            for raw in (whole if whole is not None else entry[1].push(piece)):
                if self.table.offer(raw):
                    self.count += 1
                    self.source = entry[0]
                    self.last = clock()

    def _to_stream(self, handles):
        have, total = self.table.progress()
        switched = 0
        for port, entry in handles.items():
            try:
                self.ioctl.pes(port)
                entry[1] = TsJoiner()
                switched += 1
            except (OSError, IOError, TypeError) as exc:
                self.trail.append("TS filtresi kurulamadi %s: %s" % (entry[0], exc))
        if switched:
            self.mode = "ts"
        self.trail.append("bolum filtresi yetersiz (%.1f sn, %d/%d bolum, %d tekrar) - TS moduna gecildi: %d aygit"
                          % (self.spent, have, total, self.table.repeats, switched))

    def _single(self, piece):
        buf = bytearray(piece)
        if len(buf) < 3 or buf[0] != TABLE:
            self.odd_reads += 1
            return None
        declared = 3 + ((buf[1] & 0x0F) << 8 | buf[2])
        if len(buf) == declared:
            return [bytes(buf)]
        if len(buf) == declared - 4:
            self.stripped += 1
            return [bytes(buf)]
        self.odd_reads += 1
        return None

    def run(self):
        handles = {}
        try:
            handles = self._attach()
            if not handles:
                self.fault = "Demux açılamadı (%s)." % ", ".join(self.paths)
                return
            begin = self.last = clock()
            relaxed = False
            while not self.halt.is_set():
                now = clock()
                self.spent = now - begin
                if self.spent > self.limit:
                    growing = now - self.table.grew_at < 15.0
                    if not growing or self.spent > self.limit * 2 or self.table.done():
                        break
                if self.table.done() and now - self.table.fresh_at >= self.calm:
                    break
                if not self.table.parts and now - self.last > self.idle:
                    break
                if self.mode == "section" and not self.table.done() and self.spent > self.switch:
                    self._to_stream(handles)
                starving = not self.table.parts and self.table.suspect > 0 and self.spent > 6.0
                if not relaxed and not self.table.done() and (self.spent > self.relax or starving):
                    relaxed = True
                    self._relax(handles)
                try:
                    ready = select.select(list(handles), [], [], 0.25)[0]
                except (OSError, IOError, ValueError, select.error) as exc:
                    if getattr(exc, "errno", None) == errno.EINTR or (exc.args and exc.args[0] == errno.EINTR):
                        continue
                    raise
                for ready_port in ready:
                    self._drain(ready_port, handles[ready_port])
            self.whole = self.table.done()
            self.verified = self.whole and self.table.sound()
            self.trail.append("okuma: mod %s, %d read, %d sinir disi, %d CRC'siz gelen, %d supheli, tampon tasmasi %d"
                              % (self.mode, self.reads, self.odd_reads, self.stripped, self.table.suspect, self.overflows))
            if self.mode == "ts":
                joiners = [e[1] for e in handles.values() if isinstance(e[1], TsJoiner)]
                self.trail.append("TS: %d paket, %d sureklilik kopmasi"
                                  % (sum(j.packets for j in joiners), sum(j.breaks for j in joiners)))
            if not self.whole and self.table.parts:
                gaps = self.table.missing()
                self.trail.append("eksik bolumler (%d): %s" % (len(gaps), " ".join(gaps[:40])))
        except Exception as exc:
            self.fault = "%s: %s" % (type(exc).__name__, exc)
        finally:
            for port in handles:
                self.ioctl.disarm(port)
                try:
                    os.close(port)
                except OSError:
                    pass
            self.over = True
