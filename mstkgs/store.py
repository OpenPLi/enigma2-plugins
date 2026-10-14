import os

from .compat import clone, dump, slurp, uni
from .table import ORBIT, RADIO_KINDS, TV_KINDS

TOLERANCE = 3000
GAP = u"#SERVICE 1:832:D:0:0:0:0:0:0:0:\n#DESCRIPTION  \n"
GAP_LIMIT = 9999
BAK = ".tkgsbak"
DB_FILES = ("lamedb", "lamedb5")
CORE_FILES = DB_FILES + ("bouquets.tv", "bouquets.radio")
SHARED_TSIDS = frozenset((1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 15, 22, 1001))


def _hex_key(parts):
    if len(parts) != 3:
        return None
    try:
        return tuple(int(x, 16) for x in parts)
    except ValueError:
        return None


def _orbit(raw):
    value = int(raw)
    return value + 3600 if value < 0 else value


class Mux(object):
    __slots__ = ("ident", "khz", "baud", "plane", "orbit", "gen", "inner", "mode", "roll", "pilot")

    def __init__(self, key, fields):
        self.ident = key
        self.khz, self.baud, self.plane = int(fields[0]), int(fields[1]), int(fields[2])
        self.orbit = _orbit(fields[4])

        def pick(index, fallback):
            return int(fields[index]) if len(fields) > index and fields[index].lstrip("-").isdigit() else fallback

        self.inner = pick(3, 0)
        self.gen = pick(7, 0)
        self.mode = pick(8, 1)
        self.roll = pick(9, 0)
        self.pilot = pick(10, 2)

    def recipe(self):
        return ("db", self.khz, self.baud, self.plane, self.inner, self.gen, self.mode, self.roll, self.pilot)


class Service(object):
    __slots__ = ("svc_id", "space", "ts_id", "net_id", "kind", "name")

    def __init__(self, sid, ns, tsid, onid, kind, name):
        self.svc_id, self.space, self.ts_id, self.net_id, self.kind, self.name = sid, ns, tsid, onid, kind, name

    @property
    def transport(self):
        return (self.space, self.ts_id, self.net_id)

    @property
    def reference(self):
        return "1:0:%X:%X:%X:%X:%X:0:0:0:" % (self.kind, self.svc_id, self.ts_id, self.net_id, self.space)

    @property
    def radio(self):
        return self.kind in RADIO_KINDS

    @classmethod
    def from_head(cls, head, name):
        bits = head.split(":")
        if len(bits) < 5:
            return None
        try:
            hexes = [int(b, 16) for b in bits[:4]]
            return cls(hexes[0], hexes[1], hexes[2], hexes[3], int(bits[4]), name)
        except ValueError:
            return None


class Channels(object):
    def __init__(self):
        self.muxes = {}
        self.entries = []

    @classmethod
    def read(cls, folder):
        plain, modern = [os.path.join(folder, n) for n in DB_FILES]
        stamps = dict((p, os.path.getmtime(p)) for p in (plain, modern) if os.path.exists(p))
        if not stamps:
            return cls.parse(u"")
        chosen = modern if stamps.get(modern, -1) >= stamps.get(plain, -1) else plain
        return cls.parse(slurp(chosen))

    @classmethod
    def parse(cls, content):
        db = cls()
        content = uni(content)
        (db._v5 if content.startswith("eDVB services /5/") else db._v4)(content.splitlines())
        return db

    def _mux(self, key, line):
        fields = line.split(":")
        if key and len(fields) >= 5:
            try:
                self.muxes[key] = Mux(key, fields)
            except ValueError:
                pass

    def _v4(self, rows):
        zone = None
        cursor, count = 0, len(rows)
        while cursor < count:
            row = rows[cursor]
            following = rows[cursor + 1] if cursor + 1 < count else None
            step = 1
            if row == "transponders" or row == "services":
                zone = row
            elif row == "end":
                zone = None
            elif zone == "transponders" and row and row[0] not in "\t/":
                if following is not None and following[:3] == "\ts ":
                    self._mux(_hex_key(row.split(":")[:3]), following[3:])
            elif zone == "services" and row and ":" in row and following is not None:
                entry = Service.from_head(row, following.strip())
                if entry is not None:
                    self.entries.append(entry)
                    step = 3
            cursor += step

    def _v5(self, rows):
        for row in rows:
            kind, body = row[:2], row[2:]
            if kind not in ("t:", "s:"):
                continue
            pieces = body.split(",", 1)
            head, tail = pieces[0], (pieces[1] if len(pieces) > 1 else u"")
            if kind == "t:":
                if tail[:2] == "s:":
                    self._mux(_hex_key(head.split(":")[:3]), tail[2:])
                continue
            label = u""
            if tail[:1] == '"':
                end = tail.find('"', 1)
                label = tail[1:end] if end > 0 else tail[1:]
            entry = Service.from_head(head, label)
            if entry is not None:
                self.entries.append(entry)

    def locate(self, mhz, pol, ks, orbpos=ORBIT):
        target = 1 if pol.upper() == "V" else 0
        best = None
        for mux in self.muxes.values():
            if mux.orbit != orbpos or mux.plane != target:
                continue
            gap = abs(mux.khz - mhz * 1000)
            if gap > TOLERANCE or abs(mux.baud - ks * 1000) > 1000:
                continue
            if best is None or gap < abs(best.khz - mhz * 1000):
                best = mux
        return best

    def zap_target(self, mux):
        pool = [s for s in self.entries if s.transport == mux.ident]
        pool.sort(key=lambda s: 0 if s.kind in TV_KINDS else (1 if s.kind in RADIO_KINDS else 2))
        return pool[0] if pool else None


def _trusted_ids(orbit, net_id, ts_id):
    if net_id == 0 or net_id == 0x1111:
        return False
    if net_id != 42:
        return net_id < 0xFF00
    return not (orbit == 420 and ts_id in SHARED_TSIDS)


def namespace(orbpos, khz, pol, onid, tsid):
    space = (orbpos % 0x10000) * 0x10000
    if not _trusted_ids(orbpos, onid, tsid):
        space |= (khz // 1000) % 0x10000 | (pol % 2) * 0x8000
    return space


class Link(object):
    __slots__ = ("program", "service", "fresh")

    def __init__(self, program, service, fresh):
        self.program, self.service, self.fresh = program, service, fresh

    @property
    def radio(self):
        return self.program.radio


class Blueprint(object):
    def __init__(self, catalog):
        self.catalog = catalog
        self.links = []
        self.by_number = {}
        self.add_muxes = {}
        self.fix_muxes = {}
        self.add_services = {}

    def tally(self, fresh):
        return sum(1 for link in self.links if link.fresh == fresh)

    def order(self, name):
        rows = self.catalog.orders.get(name)
        if not rows:
            rows = [(l.program.chno, l.program.chno) for l in self.links]
        return sorted(rows)

    def walk(self, name, radio=None, category=None, skip_scrambled=False):
        for pos, lcn in self.order(name):
            link = self.by_number.get(lcn)
            if link is None:
                continue
            if radio is not None and link.radio != radio:
                continue
            if category is not None and link.program.genre_id != category:
                continue
            if skip_scrambled and link.program.encrypted:
                continue
            yield pos, link

    @classmethod
    def build(cls, catalog, db):
        plan = cls(catalog)
        index = {}
        for svc in db.entries:
            index.setdefault(svc.transport, {})[svc.svc_id] = svc
        grouped = {}
        for prog in catalog.programs:
            if not prog.data:
                grouped.setdefault(prog.carrier.rank, []).append(prog)
        for car in catalog.carriers:
            progs = grouped.get(car.rank)
            if not progs:
                continue

            def near(m):
                return m.orbit == car.orbit and m.plane == car.plane and abs(m.khz - car.khz) <= TOLERANCE

            known = sorted((m for m in db.muxes.values() if near(m)),
                           key=lambda m: -sum(1 for p in progs if p.svc_id in index.get(m.ident, {})))
            pending = [k for k, c in plan.add_muxes.items()
                       if c.orbit == car.orbit and c.plane == car.plane and abs(c.khz - car.khz) <= TOLERANCE]
            if known:
                home = known[0].ident
                if abs(known[0].baud - car.baud) > 500000 or known[0].gen != car.gen:
                    plan.fix_muxes[home] = car
            elif pending:
                home = pending[0]
            else:
                tsid, onid = 0x0F00 + car.rank, 0
                home = (namespace(car.orbit, car.khz, car.plane, onid, tsid), tsid, onid)
                plan.add_muxes[home] = car
            for prog in progs:
                hit = None
                for mux in known:
                    hit = index.get(mux.ident, {}).get(prog.svc_id)
                    if hit is not None:
                        break
                if hit is None:
                    ns, tsid, onid = home
                    hit = Service(prog.svc_id, ns, tsid, onid, prog.kind or 1, prog.name)
                    plan.add_services[(prog.svc_id, ns, tsid, onid)] = (hit, prog.brand)
                    link = Link(prog, hit, True)
                else:
                    link = Link(prog, hit, False)
                plan.links.append(link)
                plan.by_number[prog.chno] = link
        plan.links.sort(key=lambda l: l.program.chno)
        return plan


def bouquet(title, plan, order, radio=False, gaps=True, skip_scrambled=False, category=None):
    out = [u"#NAME %s\n" % uni(title)]
    slot = 0
    count = 0
    for pos, link in plan.walk(order, radio=radio, category=category, skip_scrambled=skip_scrambled):
        if gaps and category is None and pos <= GAP_LIMIT:
            while slot + 1 < pos:
                out.append(GAP)
                slot += 1
        out.append(u"#SERVICE %s\n#DESCRIPTION %s\n" % (link.service.reference, uni(link.program.name)))
        slot += 1
        count += 1
    return u"".join(out), count


def index_line(name):
    return u'#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet\n' % name


def merge_index(content, names, top=True, prefix=None):
    names = [names] if isinstance(names, (str, type(u""))) else list(names)
    rows = uni(content).splitlines(True) if content else []
    if rows and not rows[-1].endswith("\n"):
        rows[-1] += "\n"
    keep = [r for r in rows if not any(('"%s"' % n) in r for n in names)
            and not (prefix and ('"%s' % prefix) in r)]
    if not keep or not keep[0].startswith("#NAME"):
        keep.insert(0, u"#NAME User - bouquets (%s)\n" % ("TV" if names and names[0].endswith(".tv") else "Radio"))
    fresh = [index_line(n) for n in names]
    keep = keep[:1] + fresh + keep[1:] if top else keep + fresh
    return u"".join(uni(r) for r in keep)


def _sat(car):
    parts = [car.khz, car.baud, car.plane, car.inner, car.orbit, 2, 0]
    if car.gen:
        parts += [1, car.mode, car.roll, 2]
    return ":".join(str(x) for x in parts)


class Editor(object):
    def __init__(self, content):
        content = uni(content)
        self.v5 = content.startswith("eDVB services /5/")
        self.rows = content.splitlines()

    def render(self):
        return u"\n".join(uni(r) for r in self.rows) + u"\n"

    def _block(self, word):
        if word not in self.rows:
            return -1, -1
        start = self.rows.index(word)
        for i in range(start + 1, len(self.rows)):
            if self.rows[i] == "end":
                return start, i
        return start, len(self.rows)

    def _skeleton(self):
        if "transponders" not in self.rows or "services" not in self.rows:
            self.rows = [u"eDVB services /4/", u"transponders", u"end", u"services", u"end"]

    def _tail(self, heads):
        return max([i for i, r in enumerate(self.rows) if r.startswith(heads)] or [0])

    def retune(self, key, car):
        tag = "{0:08x}:{1:04x}:{2:04x}".format(*key)
        for i, row in enumerate(self.rows):
            if self.v5 and row.startswith("t:" + tag + ","):
                self.rows[i] = u"t:%s,s:%s" % (tag, _sat(car))
                return True
            if not self.v5 and row == tag and i + 1 < len(self.rows) and self.rows[i + 1].startswith("\ts "):
                self.rows[i + 1] = u"\ts " + _sat(car)
                return True
        return False

    def add_mux(self, key, car):
        tag = "{0:08x}:{1:04x}:{2:04x}".format(*key)
        if self.v5:
            if any(r.startswith("t:" + tag + ",") for r in self.rows):
                return False
            self.rows.insert(self._tail("t:") + 1, u"t:%s,s:%s" % (tag, _sat(car)))
            return True
        self._skeleton()
        start, stop = self._block("transponders")
        if tag in self.rows[start:stop]:
            return False
        self.rows[stop:stop] = [tag, u"\ts " + _sat(car), u"/"]
        return True

    def put_service(self, svc, provider=u""):
        head = "%04x:%08x:%04x:%04x:%d:0" % (svc.svc_id, svc.space, svc.ts_id, svc.net_id, svc.kind)
        key = head.rsplit(":", 2)[0] + ":"
        name = uni(svc.name).replace(u'"', u"'").replace(u"\n", u" ")
        prov = uni(provider or "TKGS").replace(u",", u" ").replace(u"\n", u" ")
        if self.v5:
            if any(r.startswith("s:" + key) for r in self.rows):
                return False
            self.rows.insert(self._tail(("s:", "t:")) + 1, u's:%s,"%s",p:%s' % (head, name, prov))
            return True
        self._skeleton()
        start, stop = self._block("services")
        if any(self.rows[i].startswith(key) for i in range(start + 1, stop)):
            return False
        self.rows[stop:stop] = [head, name, u"p:%s" % prov]
        return True

    def merge(self, plan):
        tally = {"mux_added": 0, "mux_fixed": 0, "svc_added": 0}
        for key, car in plan.fix_muxes.items():
            tally["mux_fixed"] += self.retune(key, car)
        for key, car in plan.add_muxes.items():
            tally["mux_added"] += self.add_mux(key, car)
        for svc, provider in plan.add_services.values():
            tally["svc_added"] += self.put_service(svc, provider)
        return tally


def commit(folder, plan):
    result = None
    for name in DB_FILES:
        path = os.path.join(folder, name)
        exists = os.path.exists(path)
        if not exists and name == "lamedb5":
            continue
        editor = Editor(slurp(path) if exists else u"")
        stats = editor.merge(plan)
        if sum(stats.values()):
            dump(path, editor.render())
        if result is None:
            result = stats
    return result or {"mux_added": 0, "mux_fixed": 0, "svc_added": 0}


def canonical(ref):
    return u":".join(uni(ref).split(":")[:10]).upper() + u":"


def references(path):
    if not os.path.exists(path):
        return []
    out = []
    for row in slurp(path).splitlines():
        if row.startswith("#SERVICE "):
            parts = row[9:].strip().split(":")
            if len(parts) >= 10 and parts[1] == "0":
                out.append(canonical(row[9:].strip()))
    return out


def _owned(folder, prefix):
    try:
        return [n for n in os.listdir(folder) if n.startswith(prefix) and n.endswith((".tv", ".radio"))]
    except OSError:
        return []


def unlink_candidates(folder, prefix, keep):
    try:
        return [n for n in os.listdir(folder) if n.startswith(prefix) and n.endswith(".tv") and n not in keep]
    except OSError:
        return []


def unlink_owned(folder, prefix, keep=()):
    gone = 0
    for name in _owned(folder, prefix):
        if name in keep:
            continue
        try:
            os.remove(os.path.join(folder, name))
            gone += 1
        except OSError:
            pass
    return gone


def strip_owned(folder, prefix):
    for index in ("bouquets.tv", "bouquets.radio"):
        path = os.path.join(folder, index)
        if os.path.exists(path):
            rows = slurp(path).splitlines(True)
            kept = [r for r in rows if ('"%s' % prefix) not in r]
            if len(kept) != len(rows):
                dump(path, u"".join(kept))
    return unlink_owned(folder, prefix)


class Vault(object):
    def __init__(self, folder, prefix):
        self.folder = folder
        self.prefix = prefix

    def _path(self, name):
        return os.path.join(self.folder, name)

    def items(self):
        try:
            names = sorted(os.listdir(self.folder))
        except OSError:
            return []
        out = []
        for name in names:
            if name.endswith(BAK):
                try:
                    out.append((name[:-len(BAK)], os.path.getmtime(self._path(name))))
                except OSError:
                    pass
        return out

    def wipe(self):
        count = 0
        for name, _ in self.items():
            try:
                os.remove(self._path(name + BAK))
                count += 1
            except OSError:
                pass
        return count

    def capture(self):
        self.wipe()
        try:
            present = set(os.listdir(self.folder))
        except OSError:
            present = set()
        targets = [n for n in CORE_FILES if n in present] + _owned(self.folder, self.prefix)
        saved = 0
        for name in targets:
            try:
                clone(self._path(name), self._path(name + BAK))
                saved += 1
            except (OSError, IOError):
                pass
        return saved

    def restore(self):
        held = self.items()
        if held:
            unlink_owned(self.folder, self.prefix, keep=set(n for n, _ in held))
        count = 0
        for name, _ in held:
            try:
                clone(self._path(name + BAK), self._path(name))
                count += 1
            except (OSError, IOError):
                pass
        return count
