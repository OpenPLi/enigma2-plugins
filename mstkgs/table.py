# -*- coding: utf-8 -*-
import re

from .compat import uni
from .dvb import stitch

ORBIT = 420
TV_KINDS = frozenset((0x01, 0x04, 0x11, 0x16, 0x19, 0x1C, 0x1F, 0x20, 0x86, 0xC3))
RADIO_KINDS = frozenset((0x02, 0x0A))
HD_KINDS = frozenset((0x11, 0x19, 0x1F, 0x20, 0x86))

_NOISE = re.compile(u"[\x00-\x1f\x7f-\x9f]")
_TURKISH = {0xD0: u"\u011e", 0xDD: u"\u0130", 0xDE: u"\u015e",
            0xF0: u"\u011f", 0xFD: u"\u0131", 0xFE: u"\u015f"}


SAT_DELIVERY = 0x43


def inner_code(value):
    return value if value <= 10 or value == 0x0F else None


class Malformed(ValueError):
    pass


def _codec(raw, name):
    try:
        return bytes(raw).decode(name)
    except LookupError:
        plain = bytes(raw).decode("latin-1")
        if name.replace("_", "-").lower() in ("iso-8859-9", "iso8859-9", "latin5"):
            plain = u"".join(_TURKISH.get(ord(ch), ch) for ch in plain)
        return plain


def _tidy(value):
    return u" ".join(_NOISE.sub(u" ", uni(value)).split())[:120]


def dvb_text(raw):
    data = bytearray(raw)
    if not data:
        return u""
    lead = data[0]
    name = "iso-8859-9"
    if lead == 0x15:
        name, data = "utf-8", data[1:]
    elif lead == 0x11:
        name, data = "utf-16-be", data[1:]
    elif lead == 0x10:
        if len(data) < 3 or data[1] != 0 or data[2] in (0, 12) or data[2] > 15:
            return u""
        name, data = "iso-8859-%d" % data[2], data[3:]
    elif 0x01 <= lead <= 0x0B:
        if lead + 4 == 12:
            return u""
        name, data = "iso-8859-%d" % (lead + 4), data[1:]
    elif lead < 0x20:
        return u""
    try:
        return _tidy(_codec(data, name))
    except (UnicodeError, ValueError):
        try:
            return _tidy(bytes(data).decode("latin-1" if name == "utf-8" else name, "replace"))
        except Exception:
            return u""


def _decimal(chunk):
    total = 0
    for byte in bytearray(chunk):
        high, low = byte >> 4, byte & 0x0F
        if high > 9 or low > 9:
            return None
        total = total * 100 + high * 10 + low
    return total


class Carrier(object):
    __slots__ = ("rank", "khz", "baud", "plane", "inner", "orbit", "gen", "mode", "roll")

    def __init__(self, rank, **fields):
        self.rank = rank
        for key, value in fields.items():
            setattr(self, key, value)

    def label(self):
        return "%d %s %d %s" % (self.khz // 1000, "HVLR"[self.plane], self.baud // 1000, "S2" if self.gen else "S")

    @classmethod
    def from_descriptor(cls, index, body):
        body = bytearray(body)
        if len(body) != 11:
            return None
        freq, orb, rate = _decimal(body[0:4]), _decimal(body[4:6]), _decimal(body[7:10])
        tail = body[10]
        if None in (freq, orb, rate) or (tail >> 4) > 9:
            return None
        khz = freq * 10
        sr = (rate * 10 + (tail >> 4)) * 100
        if not (3000000 <= khz <= 13000000 and 1000000 <= sr <= 50000000 and orb <= 1800):
            return None
        fec = tail & 0x0F
        if inner_code(fec) is None:
            return None
        flags = body[6]
        return cls(index, khz=khz, baud=sr, inner=fec,
                   orbit=orb if flags & 0x80 else (3600 - orb) % 3600,
                   plane=(flags >> 5) & 3, roll=(flags >> 3) & 3,
                   gen=(flags >> 2) & 1, mode=flags & 3)


class Program(object):
    __slots__ = ("chno", "svc_id", "name", "kind", "brand", "encrypted", "genre_id", "carrier")

    def __init__(self, lcn, sid, info, carrier):
        self.chno = lcn
        self.svc_id = sid
        self.name = info["name"]
        self.kind = info["kind"]
        self.brand = info["provider"]
        self.encrypted = info["scrambled"]
        self.genre_id = info["category"]
        self.carrier = carrier

    @property
    def radio(self):
        return self.kind in RADIO_KINDS

    @property
    def data(self):
        return self.kind not in TV_KINDS and self.kind not in RADIO_KINDS

    @property
    def hd(self):
        return self.kind in HD_KINDS


class Catalog(object):
    def __init__(self):
        self.headline = u""
        self.bird = u""
        self.carriers = []
        self.programs = []
        self.orders = {}
        self.genres = {}
        self.notes = []

    def by_number(self):
        return dict((p.chno, p) for p in self.programs)


class _Reader(object):
    def __init__(self, data):
        self.b = bytearray(data)
        self.n = len(self.b)

    def word(self, at):
        if at + 2 > self.n:
            raise Malformed("veri erken bitti @%d" % at)
        return (self.b[at] << 8) | self.b[at + 1]

    def span12(self, at):
        return ((self.b[at] & 0x0F) << 8) | self.b[at + 1]

    def tags(self, start, stop):
        out = []
        at = start
        while at < stop:
            if at + 2 > stop or at + 2 + self.b[at + 1] > stop:
                raise Malformed("bozuk descriptor zinciri @%d" % at)
            size = self.b[at + 1]
            out.append((self.b[at], self.b[at + 2:at + 2 + size]))
            at += 2 + size
        return out

    def carrier_head(self, at):
        if at + 2 >= self.n:
            return False
        size = self.b[at]
        if size < 13 or at + 1 + size >= self.n or self.b[at + 1 + size] != 0x42:
            return False
        try:
            return any(tag == SAT_DELIVERY for tag, _ in self.tags(at + 1, at + 1 + size))
        except Malformed:
            return False


class Parser(object):
    def __init__(self, data):
        self.r = _Reader(data)
        self.out = Catalog()

    def run(self):
        try:
            self._header()
            at = self._carriers(self._first_carrier(2 + self.r.word(0)))
            self._orders(at)
        except IndexError:
            raise Malformed("veri beklenenden once bitti")
        self._finish()
        return self.out

    def _header(self):
        for tag, body in self.r.tags(2, 2 + self.r.word(0)):
            if tag == 0x90 and len(body) >= 4:
                self.out.headline = dvb_text(body[4:4 + body[3]])

    def _first_carrier(self, at):
        b = self.r.b
        for i in range(at, min(self.r.n, at + 512)):
            if self.r.carrier_head(i):
                return i
            if b[i] == 0xA0 and i + 2 + b[i + 1] <= self.r.n and b[i + 1] >= 5:
                body = b[i + 2:i + 2 + b[i + 1]]
                if 4 + body[3] <= len(body):
                    self.out.bird = dvb_text(body[4:4 + body[3]])
        raise Malformed("transponder dongusu bulunamadi")

    def _carriers(self, at):
        b = self.r.b
        while at < self.r.n and b[at] != 0x00:
            size = b[at]
            carrier = None
            for tag, body in self.r.tags(at + 1, at + 1 + size):
                if tag == SAT_DELIVERY:
                    carrier = Carrier.from_descriptor(len(self.out.carriers), body)
            if carrier is None:
                raise Malformed("gecersiz yayin parametresi @%d" % at)
            self.out.carriers.append(carrier)
            services, at = self._services(at + 1 + size)
            at = self._lineup(at, services, carrier)
        return at + 1

    def _services(self, at):
        b = self.r.b
        found = {}
        while True:
            if b[at] != 0x42:
                raise Malformed("SDT beklenirken 0x%02X @%d" % (b[at], at))
            stop = at + 3 + self.r.span12(at + 1)
            if stop > self.r.n:
                raise Malformed("SDT tasiyor @%d" % at)
            part_no, part_last = b[at + 6], b[at + 7]
            cursor = at + 11
            while cursor < stop - 4:
                cursor = self._service(cursor, stop - 4, found)
            at = stop
            if part_no >= part_last:
                return found, at

    def _service(self, at, limit, found):
        b = self.r.b
        sid = self.r.word(at)
        span = self.r.span12(at + 3)
        if at + 5 + span > limit:
            raise Malformed("servis kaydi tasiyor @%d" % at)
        info = {"kind": None, "name": u"", "provider": u"", "category": None,
                "scrambled": bool(b[at + 3] & 0x10)}
        for tag, body in self.r.tags(at + 5, at + 5 + span):
            if tag == 0x48 and len(body) >= 3:
                plen = body[1]
                info["kind"] = body[0]
                info["provider"] = dvb_text(body[2:2 + plen])
                if 2 + plen < len(body):
                    info["name"] = dvb_text(body[3 + plen:3 + plen + body[2 + plen]])
            elif tag == 0x95 and len(body) >= 8:
                info["category"] = ((body[6] << 8) | body[7]) >> 4
        found[sid] = info
        return at + 5 + span

    def _lineup(self, at, services, carrier):
        b = self.r.b
        stop = at + 2 + self.r.word(at)
        if stop > self.r.n:
            raise Malformed("kanal listesi tasiyor @%d" % at)
        cursor = at + 2
        while cursor < stop:
            lcn = self.r.word(cursor)
            if b[cursor + 2] != 0x02:
                raise Malformed("PMT beklenirken 0x%02X @%d" % (b[cursor + 2], cursor))
            sid = self.r.word(cursor + 5)
            meta = services.get(sid)
            if meta is None:
                self.out.notes.append(u"LCN %d: SID %d SDT'de yok, atlandi." % (lcn, sid))
            else:
                self.out.programs.append(Program(lcn, sid, meta, carrier))
            cursor += 5 + self.r.span12(cursor + 3)
        return stop

    def _orders(self, at):
        if at + 2 > self.r.n:
            return
        stop = min(self.r.n, at + 2 + self.r.word(at))
        cursor = at + 2
        while cursor + 2 <= stop:
            size = self.r.word(cursor) & 0x0FFF
            name, rows = None, []
            for tag, body in self.r.tags(cursor + 2, min(stop, cursor + 2 + size)):
                if tag == 0x93 and len(body) >= 4:
                    name = dvb_text(body[4:4 + body[3]])
                elif tag == 0x94 and len(body) >= 4:
                    rows.append(((body[0] << 8) | body[1], (body[2] << 8) | body[3]))
            self.out.orders[name or u"Liste %d" % (len(self.out.orders) + 1)] = rows
            cursor += 2 + size
        if stop + 2 <= self.r.n:
            for tag, body in self.r.tags(stop + 2, min(self.r.n, stop + 2 + self.r.word(stop))):
                if tag == 0x92 and len(body) >= 6:
                    self.out.genres[((body[0] << 8) | body[1]) >> 4] = dvb_text(body[6:6 + body[5]])

    def _finish(self):
        self.out.programs.sort(key=lambda p: p.chno)
        seen = {}
        for prog in self.out.programs:
            if prog.chno in seen:
                self.out.notes.append(u"LCN %d iki kez geciyor (%s / %s)." % (prog.chno, seen[prog.chno].name, prog.name))
            seen[prog.chno] = prog


def decode(raws, verify=True):
    return Parser(stitch(raws, verify)).run()
