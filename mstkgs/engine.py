# -*- coding: utf-8 -*-
import io
import json
import os
import time
import traceback

from enigma import eDVBDB, eServiceReference, eTimer

from . import dvb, store, table
from .compat import clock, dump, native, slurp, uni
from .conf import beacon_key, opts
from .diag import note
from .tuner import BEACONS, Frontend, Meter, describe_mode, letter, satellite_sockets

FOLDER = "/etc/enigma2"
PREFIX = "userbouquet.mstkgs"
TV = PREFIX + ".tv"
RADIO = PREFIX + ".radio"
GENRE = PREFIX + "_kat"
RAW_TMP = "/tmp/mstkgs_capture.bin"
RAW_KEEP = "/etc/enigma2/mstkgs_last.bin"
MEMORY = "/etc/enigma2/mstkgs.json"
REPORT = "/tmp/mstkgs_rapor.txt"

TUNER, LOCK, READ, PARSE = 1, 2, 3, 4
DIRECT, RELAY = "direct", "relay"
GATE = {"owner": None}


def claim(owner):
    if GATE["owner"] not in (None, owner):
        return False
    GATE["owner"] = owner
    return True


def release(owner):
    if GATE["owner"] == owner:
        GATE["owner"] = None


def ticker(callback):
    beat = eTimer()
    hooks = getattr(beat, "callback", None)
    if hooks is not None:
        hooks.append(callback)
    else:
        beat._link = beat.timeout.connect(callback)
    return beat


def reload_lists(services=False):
    try:
        base = eDVBDB.getInstance()
        (services and base.reloadServicelist())
        base.reloadBouquets()
    except Exception:
        pass


class Memory(object):
    @staticmethod
    def read():
        try:
            with io.open(MEMORY, "r", encoding="utf-8") as handle:
                return json.loads(handle.read()) or {}
        except Exception:
            return {}

    @classmethod
    def write(cls, **changes):
        data = cls.read()
        for key, value in changes.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
        try:
            dump(MEMORY, uni(json.dumps(data)))
        except Exception:
            pass

    @classmethod
    def forget_install(cls):
        cls.write(install_time=None, tv=None, radio=None, list=None, version=None, cats=None)


def stamp(value):
    try:
        return time.strftime("%d.%m %H:%M", time.localtime(float(value)))
    except Exception:
        return "-"


class Outcome(object):
    def __init__(self, catalog, complete, verified, progress, versions, source, beacon):
        self.catalog = catalog
        self.whole = complete
        self.verified = verified
        self.have, self.total = progress
        self.source = source
        self.beacon = beacon
        self.version = ", ".join("%d" % v for v in sorted(set(versions.values()))) or "-"

    @property
    def order(self):
        wanted = opts.order.value
        if wanted in self.catalog.orders:
            return wanted
        return next(iter(self.catalog.orders), wanted)

    def blueprint(self):
        return store.Blueprint.build(self.catalog, store.Channels.read(FOLDER))

    @classmethod
    def cached(cls):
        path = RAW_KEEP if os.path.exists(RAW_KEEP) else RAW_TMP
        if not os.path.exists(path):
            return None
        pack = dvb.Assembler(False)
        for raw in dvb.restore_blobs(path):
            pack.offer(raw)
        if not pack.ordered():
            return None
        return cls(table.decode(pack.ordered(), False), pack.done(), False, pack.progress(),
                   pack.revisions(), path, None)


def beacons():
    choice = opts.beacon.value
    picked = [b for b in BEACONS if beacon_key(b) == choice]
    return picked or list(BEACONS)


class Reader(object):
    IDLE, TUNING, GRABBING = range(3)

    def __init__(self, session, on_step, on_end, quiet=False):
        self.session = session
        self.quiet = quiet
        self.on_step = on_step
        self.on_end = on_end
        self.phase = self.IDLE
        self.queue = []
        self.size = 1
        self.current = None
        self.frontend = None
        self.grabber = None
        self.previous = None
        self.stopped = False
        self.hopped = False
        self.starved = False
        self.best = None
        self.since = 0.0
        self.timer = ticker(self._tick)

    @property
    def busy(self):
        return self.phase != self.IDLE

    def _say(self, stage, message, percent, meter=None):
        try:
            self.on_step(stage, message, percent, meter)
        except Exception:
            pass

    def _remember_service(self):
        nav = self.session.nav
        getter = getattr(nav, "getCurrentlyPlayingServiceOrGroup", None) or nav.getCurrentlyPlayingServiceReference
        self.previous = getter()

    def start(self):
        self._remember_service()
        self.stopped = self.hopped = self.starved = False
        self.best = None
        db = store.Channels.read(FOLDER)
        self.queue = []
        for b in beacons():
            known = db.locate(*b)
            if known is not None:
                self.queue.append((DIRECT, b, known.recipe()))
            self.queue += [(DIRECT, b, mode) for mode in ("s", "s2")]
        for freq, pol, sr in ([] if self.quiet else beacons()):
            mux = db.locate(freq, pol, sr)
            target = mux and db.zap_target(mux)
            if target is not None:
                self.queue.append((RELAY, (freq, pol, sr), target))
        self.size = max(1, len(self.queue))
        self.phase = self.TUNING
        note("okuma", "basladi", sessiz=self.quiet, frekanslar=" / ".join("%d%s%d" % b for b in beacons()),
             yedek_kanal=sum(1 for q in self.queue if q[0] == RELAY), tunerler=",".join(letter(s) for s in satellite_sockets()) or "-")
        self._say(TUNER, "Türksat 42.0E tuneri hazırlanıyor...", 3)
        self._advance()

    def _frontend(self):
        for halt in ((False,) if self.quiet else (False, True)):
            if halt and not self.stopped:
                nav = self.session.nav
                nav.stopService()
                self.stopped = True
                time.sleep(0.35)
            fe = Frontend.grab(satellite_sockets())
            if fe is not None:
                note("tuner", "ham kanal ayrildi", tuner=letter(fe.socket), yayin_durduruldu=self.stopped)
                return fe
            note("tuner", "ham kanal ayrilamadi", yayin_durduruldu=self.stopped)
        return None

    def _drop_frontend(self):
        if self.frontend is not None:
            self.frontend.release()
            self.frontend = None

    def _only_zap(self):
        self.queue = [q for q in self.queue if q[0] == RELAY]

    def _advance(self):
        self._drop_frontend()
        if not self.queue:
            return self._conclude(None)
        self.current = self.queue.pop(0)
        kind, (freq, pol, sr), extra = self.current
        percent = 5 + min(20, (self.size - len(self.queue)) * 20 // self.size)
        if kind == DIRECT:
            self.frontend = self._frontend()
            if self.frontend is None:
                self.starved = True
                self._only_zap()
                return self._advance()
            self._say(LOCK, "%d %s %d  ·  %s  ·  Tuner %s" % (
                freq, pol, sr, describe_mode(extra), letter(self.frontend.socket)), percent)
            note("ayar", "%d %s %d" % (freq, pol, sr), sistem=describe_mode(extra), tuner=letter(self.frontend.socket))
            self.frontend.aim(freq, pol, sr, extra)
        else:
            note("ayar", "%d %s %d" % (freq, pol, sr), yol="kanal listesi", servis=extra.reference)
            self._say(LOCK, "%d %s %d  ·  kanal listesi üzerinden geçiliyor" % (freq, pol, sr), percent)
            self.hopped = True
            self.session.nav.playService(eServiceReference(extra.reference))
        self.phase = self.TUNING
        self.since = clock()
        self.timer.start(300, False)

    def _live_status(self):
        try:
            service = self.session.nav.getCurrentService()
            probe = service and service.frontendInfo()
            if probe is None:
                return None
            reader = getattr(probe, "getFrontendStatus", None)
            return (reader() if reader else probe.getAll(False)) or None
        except Exception:
            return None

    def _live_demux(self):
        try:
            service = self.session.nav.getCurrentService()
            stream = service and service.stream()
            facts = stream and stream.getStreamingData()
            if facts:
                return (int(facts.get("adapter") or 0), facts.get("demux"))
        except Exception:
            pass
        return (0, None)

    def _meter(self):
        return Meter.read(self.frontend.readout() if self.frontend is not None else self._live_status())

    def _grab(self, paths):
        try:
            limit = float(opts.patience.value)
        except (TypeError, ValueError):
            limit = 60.0
        note("okuma", "demux", aygitlar=", ".join(paths), sinir=limit)
        self.grabber = dvb.Grabber(paths, limit=limit, relax=min(25.0, limit * 0.45))
        self.grabber.start()
        self.phase = self.GRABBING
        self._say(READ, "Kilitlendi. TKGS tablosu okunuyor...", 26, self._meter())

    def _tick(self):
        if self.current is None:
            return self.timer.stop()
        try:
            if self.phase == self.TUNING:
                return self._tick_tuning(clock() - self.since)
            if self.phase == self.GRABBING:
                return self._tick_grabbing()
        except Exception:
            note("hata", traceback.format_exc())
            raise

    def _tick_tuning(self, waited):
        kind, beacon, _ = self.current
        if kind == DIRECT:
            phase = self.frontend.lock_state() if self.frontend else None
            if phase == "LOCKED":
                demux = self.frontend.reserve()
                m = self._meter()
                note("kilit", "%d %s %d" % beacon, sure="%.1f" % waited, demux=demux,
                     kalite=m and m.quality, guc=m and m.power, snr_db=m and m.db)
                if demux is None or demux < 0:
                    self._only_zap()
                    self.timer.stop()
                    return self._advance()
                return self._grab(["/dev/dvb/adapter0/demux%d" % demux])
            if phase == "FAILED" or waited > 7.0:
                m = self._meter()
                note("kilit", "%d %s %d yok" % beacon, durum=phase, sure="%.1f" % waited,
                     kalite=m and m.quality, guc=m and m.power)
                self.timer.stop()
                return self._advance()
            return self._say(LOCK, None, None, self._meter())
        status = self._live_status()
        state = status and status.get("tuner_state")
        locked = None if state is None else state == "LOCKED"
        if locked is True or (locked is None and waited > 4.0):
            adapter, demux = self._live_demux()
            note("kilit", "%d %s %d (kanal listesi)" % beacon, durum=state, adapter=adapter, demux=demux)
            return self._grab(dvb.demuxes(adapter, demux))
        if waited > 12.0:
            note("kilit", "%d %s %d yok (kanal listesi)" % beacon, durum=state)
            self.timer.stop()
            self._advance()

    def _tick_grabbing(self):
        beacon = self.current[1]
        g = self.grabber
        snap = g.snapshot()
        if not g.over:
            total = snap["total"] or 0
            percent = 26 + (int(70 * snap["have"] / total) if total else min(30, int(snap["elapsed"])))
            return self._say(READ, "%d %s %d  ·  %s / %s bölüm  ·  %.0f sn%s" % (
                beacon[0], beacon[1], beacon[2], snap["have"], total or "?", snap["elapsed"],
                ("  ·  TS modu" if snap.get("mode") == "ts" else "") + ("" if snap["crc"] else "  ·  oylama")),
                min(96, percent), self._meter())
        self.timer.stop()
        if not g.whole and not g.fault:
            if g.table.ordered() and (self.best is None or g.table.progress()[0] > self.best.table.progress()[0]):
                self.best = g
            others = [q for q in self.queue if q[1] != beacon]
            if others:
                note("okuma", "%d %s %d tamamlanamadi, sonraki frekansa geciliyor" % beacon,
                     bolum="%d/%d" % g.table.progress())
                self.queue = others
                return self._advance()
            if self.best is not None:
                g = self.best
        self._conclude(g)

    def _restore(self):
        self._drop_frontend()
        if self.previous is not None and (self.stopped or self.hopped):
            try:
                self.session.nav.playService(self.previous)
            except Exception:
                pass
        elif self.previous is None and self.hopped:
            nav = self.session.nav
            try:
                nav.stopService()
            except Exception:
                pass
        self.previous = None
        self.stopped = self.hopped = False

    def abort(self):
        self.timer.stop()
        if self.grabber is not None and not self.grabber.over:
            self.grabber.abort()
        if self.phase != self.IDLE:
            self.phase = self.IDLE
            self._restore()

    def _conclude(self, g):
        if g is not None:
            have, total = g.table.progress()
            note("okuma", "bitti", bolum="%d/%d" % (have, total), tam=g.whole, crc=g.verified, gecerli=g.count,
                 reddedilen=g.table.dropped, tekrar=g.table.repeats, tasma=g.overflows, sure="%.1f" % g.spent,
                 kaynak=g.source or "-", hata=g.fault or "-")
            for line in g.trail:
                note("demux", line)
        else:
            note("okuma", "hicbir frekansta kilit yok", tuner_yok=self.starved)
        self.phase = self.IDLE
        self._restore()
        if g is None and self.quiet and self.starved:
            return self.on_end(None, "Boş tuner yok; izlenen yayın bölünmedi.")
        if g is None:
            return self.on_end(None, "TKGS frekanslarının hiçbirine kilitlenilemedi (%d frekans denendi).\n" % len(beacons()) +
                                     "Çanak yönünü ve 42.0E sinyalini kontrol edin.\n"
                                     "Menüdeki Sinyal Testi ile canlı ölçüm yapabilirsiniz.")
        if g.fault:
            return self.on_end(None, "Okuma hatası: %s" % native(g.fault))
        raws = g.table.ordered()
        if not raws:
            return self.on_end(None, "Kilitlenildi ancak TKGS verisi gelmedi (%.0f sn)." % g.spent)
        if not g.whole:
            for path in (RAW_TMP,):
                try:
                    dvb.save(path, raws)
                except (OSError, IOError):
                    pass
            have, total = g.table.progress()
            return self.on_end(None, "TKGS tablosu tamamlanamadı: %d / %d bölüm alındı (%.0f sn).\n"
                                     "Sinyal zayıf olabilir. Ayarlar'dan okuma süresini artırıp tekrar deneyin.\n"
                                     "Sorun sürerse Tanı kaydını açıp kaydı gönderin." % (have, total, g.spent))
        self._say(PARSE, "Tablo çözümleniyor...", 97)
        for path in (RAW_TMP, RAW_KEEP):
            try:
                dvb.save(path, raws)
            except (OSError, IOError):
                pass
        try:
            catalog = table.decode(raws, False)
        except (table.Malformed, IndexError) as exc:
            note("tablo", "cozulemedi", hata=exc)
            return self.on_end(None, "TKGS tablosu okundu ama çözülemedi (%s).\nHam veri: %s" % (native(str(exc)), RAW_TMP))
        note("tablo", catalog.headline or "-", kanal=len(catalog.programs), transponder=len(catalog.carriers),
             listeler=",".join(catalog.orders) or "-", kategori=len(catalog.genres), uyari=len(catalog.notes))
        if not g.whole:
            catalog.notes.insert(0, u"Tablo eksik okundu; liste eksik olabilir. Tekrar deneyin.")
        result = Outcome(catalog, g.whole, g.verified, g.table.progress(), g.table.revisions(),
                         g.source, self.current[1] if self.current else None)
        Memory.write(read_time=time.time(), read_title=uni(catalog.headline or ""), read_version=result.version)
        self._say(PARSE, "Hazır.", 100)
        self.on_end(result, None)


def delta(plan, order):
    skip = not opts.scrambled.value
    fresh = set(store.canonical(l.service.reference) for _, l in plan.walk(order, radio=False, skip_scrambled=skip))
    known = set(store.references(os.path.join(FOLDER, TV)))
    if not known:
        return None
    return len(fresh - known), len(known - fresh)


def write_report(result, plan):
    cat = result.catalog
    order = result.order
    tv = sum(1 for l in plan.links if not l.radio)
    out = [
        uni(cat.headline or u"TKGS listesi"),
        u"TKGS sürümü %s  ·  %d/%d bölüm%s  ·  %s" % (uni(result.version), result.have, result.total,
                                                    u"" if result.whole else u" (EKSİK)",
                                                    u"CRC doğrulandı" if result.verified else u"CRC'siz"),
        u"%d TV + %d radyo kanalı  ·  %d transponder  ·  Liste: %s" % (tv, len(plan.links) - tv,
                                                                      len(cat.carriers), uni(order)),
        u"Listede vardı: %d  ·  Eklenecek: %d kanal, %d transponder  ·  Güncellenecek: %d transponder" % (
            plan.tally(False), plan.tally(True), len(plan.add_muxes), len(plan.fix_muxes)),
        u"",
    ]
    for wants_radio in (False, True):
        out.append(u"===== %s =====" % (u"RADYO" if wants_radio else u"TV"))
        for pos, link in plan.walk(order, radio=wants_radio):
            prog = link.program
            genre = cat.genres.get(prog.genre_id, u"")
            out.append(u"%4d  %s%s%s%s" % (pos, prog.name, u"  · " + genre if genre else u"",
                                           u"  [yeni]" if link.fresh else u"",
                                           u"  [şifreli]" if prog.encrypted else u""))
        out.append(u"")
    if cat.notes:
        out += [u"Uyarılar:"] + [uni(n) for n in cat.notes[:50]] + [u""]
    if result.beacon:
        b = result.beacon
        out.append(u"Okunan frekans: %d %s %d  ·  Demux: %s" % (b[0], uni(b[1]), b[2], uni(result.source or "-")))
    out.append(u"Ham veri: %s" % RAW_KEEP)
    body = u"\n".join(uni(r) for r in out) + u"\n"
    try:
        dump(REPORT, body)
    except (OSError, IOError):
        pass
    return body


def _index(name, files, top):
    path = os.path.join(FOLDER, name)
    content = slurp(path) if os.path.exists(path) else u""
    dump(path, store.merge_index(content, files, top=top, prefix=PREFIX))


def install(result, plan):
    gaps = opts.numbering.value
    top = opts.top.value or gaps
    skip = not opts.scrambled.value
    title = uni(opts.title.value)
    order = result.order
    try:
        if opts.backup.value:
            store.Vault(FOLDER, PREFIX).capture()
        stats = store.commit(FOLDER, plan)
        if sum(stats.values()):
            reload_lists(True)
        text, tv = store.bouquet(title, plan, order, radio=False, gaps=gaps, skip_scrambled=skip)
        dump(os.path.join(FOLDER, TV), text)
        files = [TV]
        if opts.genres.value:
            for cid, name in sorted(result.catalog.genres.items()):
                text, n = store.bouquet(u"%s - %s" % (title, name), plan, order, category=cid, skip_scrambled=skip)
                if n:
                    files.append("%s%d.tv" % (GENRE, cid))
                    dump(os.path.join(FOLDER, files[-1]), text)
        for stale in store.unlink_candidates(FOLDER, GENRE, files):
            try:
                os.remove(os.path.join(FOLDER, stale))
            except OSError:
                pass
        _index("bouquets.tv", files, top)
        radio = 0
        if opts.radio.value:
            text, radio = store.bouquet(u"%s Radyo" % title, plan, order, radio=True, gaps=gaps, skip_scrambled=skip)
            if radio:
                dump(os.path.join(FOLDER, RADIO), text)
                _index("bouquets.radio", [RADIO], top)
    except (OSError, IOError) as exc:
        note("kurulum", "hata", hata=exc)
        return False, "Kanal listesi yazılamadı: %s" % native(str(exc))
    reload_lists()
    genres = len(files) - 1
    note("kurulum", "tamam", liste=order, tv=tv, radyo=radio, kategori=genres, yedek=opts.backup.value,
         eklenen_kanal=stats["svc_added"], eklenen_tp=stats["mux_added"], guncellenen_tp=stats["mux_fixed"])
    Memory.write(install_time=time.time(), title=uni(result.catalog.headline or ""), version=result.version,
                 list=uni(order), tv=tv, radio=radio, cats=genres)
    return True, ("Kanal listesi güncellendi  ·  %s listesi\n\n%d TV%s kanalı%s\n"
                  "Eklenen: %d kanal, %d transponder  ·  Güncellenen: %d transponder%s" % (
                      native(order), tv, (", %d radyo" % radio) if radio else "",
                      (", %d kategori buketi" % genres) if genres else "",
                      stats["svc_added"], stats["mux_added"], stats["mux_fixed"],
                      "\n\nÖnceki liste yedeklendi (Yönetim > Yedekten geri yükle)." if opts.backup.value else ""))
