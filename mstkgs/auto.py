# -*- coding: utf-8 -*-
import datetime
import time

from . import engine
from .compat import clock, native, uni
from .conf import NAME, WEEKDAYS, opts
from .diag import note

try:
    from Tools import Notifications
except ImportError:
    Notifications = None

try:
    from Screens.MessageBox import MessageBox
except ImportError:
    MessageBox = None

OWNER = "auto"
RETRY = 3600
WARMUP = 120


def standby():
    try:
        import Screens.Standby as module
        return getattr(module, "inStandby", None) is not None
    except Exception:
        return False


class Planner(object):
    @staticmethod
    def _clock():
        hour, minute = opts.auto_time.value.split(":")
        return int(hour), int(minute)

    @staticmethod
    def _epoch(moment):
        return time.mktime(moment.timetuple())

    @staticmethod
    def _shift_month(moment, delta, day):
        month = moment.month - 1 + delta
        return moment.replace(year=moment.year + month // 12, month=month % 12 + 1, day=day)

    @classmethod
    def previous(cls, now=None):
        mode = opts.auto.value
        if mode == "off":
            return None
        now = now or datetime.datetime.now()
        hour, minute = cls._clock()
        mark = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if mode == "daily":
            if mark > now:
                mark -= datetime.timedelta(days=1)
        elif mode == "weekly":
            mark -= datetime.timedelta(days=(now.weekday() - int(opts.auto_day.value)) % 7)
            if mark > now:
                mark -= datetime.timedelta(days=7)
        else:
            day = int(opts.auto_date.value)
            mark = mark.replace(day=day)
            if mark > now:
                mark = cls._shift_month(mark, -1, day)
        return mark

    @classmethod
    def following(cls, now=None):
        last = cls.previous(now)
        if last is None:
            return None
        mode = opts.auto.value
        if mode == "daily":
            return last + datetime.timedelta(days=1)
        if mode == "weekly":
            return last + datetime.timedelta(days=7)
        return cls._shift_month(last, 1, int(opts.auto_date.value))

    @classmethod
    def due_mark(cls):
        last = cls.previous()
        return None if last is None else cls._epoch(last)

    @staticmethod
    def summary():
        mode = opts.auto.value
        at = opts.auto_time.value
        if mode == "off":
            return "Kapalı"
        if mode == "daily":
            return "Her gün %s" % at
        if mode == "weekly":
            return "Her %s %s" % (WEEKDAYS[int(opts.auto_day.value)], at)
        return "Her ayın %s. günü %s" % (opts.auto_date.value, at)

    @classmethod
    def upcoming(cls):
        nxt = cls.following()
        return nxt.strftime("%d.%m %H:%M") if nxt else "-"


class Watcher(object):
    instance = None

    def __init__(self, owner_session):
        session = owner_session
        self.session = session
        self.booted = clock()
        self.reader = None
        self.listeners = []
        self.manual = False
        self.timer = engine.ticker(self.check)
        self.timer.start(60000, False)

    @classmethod
    def boot(cls, session):
        if cls.instance is None:
            cls.instance = cls(session)
        return cls.instance

    @property
    def running(self):
        return self.reader is not None

    def _recording_soon(self):
        nav = self.session.nav
        try:
            if nav.getRecordings():
                return True
        except Exception:
            pass
        try:
            upcoming = nav.RecordTimer.getNextRecordingTime()
            return 0 < upcoming - time.time() < 600
        except Exception:
            return False

    def check(self):
        if self.running or opts.auto.value == "off" or clock() - self.booted < WARMUP:
            return
        mark = Planner.due_mark()
        mem = engine.Memory.read()
        if mark is None or mem.get("auto_slot", 0) >= mark:
            return
        failed = mem.get("auto_fail", 0)
        if failed >= mark and time.time() - failed < RETRY:
            return
        if opts.auto_standby.value and not standby():
            return
        if self._recording_soon():
            return
        self.launch(mark)

    def run_now(self, listener=None):
        if self.running:
            return False
        if listener is not None:
            self.listeners.append(listener)
        self.manual = True
        return self.launch(None)

    def launch(self, mark):
        if not engine.claim(OWNER):
            return False
        self.mark = mark
        note("otomatik", "basladi", elle=self.manual, bekleme=standby(), plan=Planner.summary())
        self.reader = engine.Reader(self.session, lambda *a: None, self._done, quiet=not standby())
        engine.Memory.write(auto_last=time.time(), auto_note=u"Kontrol ediliyor...")
        try:
            self.reader.start()
        except Exception as exc:
            self._done(None, "Başlatılamadı: %s" % exc)
        return True

    def _done(self, result, error):
        try:
            if error:
                self._finish(False, uni(native(error).split("\n")[0]))
                return
            mem = engine.Memory.read()
            same = (uni(result.version) == uni(mem.get("version", "")) and
                    uni(result.catalog.headline or "") == uni(mem.get("title", "")))
            if same and opts.auto_changed.value and mem.get("install_time"):
                self._finish(True, u"Değişiklik yok  ·  TKGS v%s" % uni(result.version))
                return
            plan = result.blueprint()
            engine.write_report(result, plan)
            if not plan.links:
                self._finish(False, u"Kurulabilir kanal bulunamadı")
                return
            ok, message = engine.install(result, plan)
            if not ok:
                self._finish(False, uni(native(message)))
                return
            tv = sum(1 for link in plan.links if not link.radio)
            self._finish(True, u"Güncellendi  ·  TKGS v%s  ·  %d TV, %d yeni kanal" % (
                uni(result.version), tv, plan.tally(True)), notify=True)
        finally:
            self.reader = None
            engine.release(OWNER)
            listeners, self.listeners = self.listeners, []
            for listener in listeners:
                try:
                    listener()
                except Exception:
                    pass

    def _finish(self, ok, message, notify=False):
        note("otomatik", "sonuc", basarili=ok, mesaj=message)
        changes = {"auto_last": time.time(), "auto_note": message, "auto_ok": ok}
        if ok and self.mark is not None:
            changes["auto_slot"] = self.mark
            changes["auto_fail"] = None
        elif not ok:
            changes["auto_fail"] = time.time()
        engine.Memory.write(**changes)
        manual, self.manual = self.manual, False
        if (notify or manual) and opts.auto_notify.value and Notifications is not None and MessageBox is not None:
            try:
                Notifications.AddPopup(native(u"%s\n%s" % (uni(NAME), message)),
                                       MessageBox.TYPE_INFO if ok else MessageBox.TYPE_WARNING, 10, "MSTKGSAuto")
            except Exception:
                pass


def status_line():
    mem = engine.Memory.read()
    if opts.auto.value == "off":
        return "Otomatik güncelleme: Kapalı"
    parts = ["Otomatik: %s" % Planner.summary(), "sonraki %s" % Planner.upcoming()]
    if mem.get("auto_last"):
        parts.append("son %s %s" % (engine.stamp(mem["auto_last"]), native(mem.get("auto_note", ""))))
    return "  ·  ".join(parts)
