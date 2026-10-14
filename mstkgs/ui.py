# -*- coding: utf-8 -*-
import math
import os
import time

from enigma import ePoint

from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ScrollLabel import ScrollLabel
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

from . import auto, engine, layout as L, store
from .compat import clock, native, slurp, uni
from .diag import Journal, note
from .conf import AUTHOR, AUTO_FIELDS, FIELDS, HANDLE, NAME, VERSION, opts, persist
from .skin import CENTER, RIGHT, Theme, cell, listbox, paint, picture, step, swap, shape_list
from .tuner import BEACONS, Frontend, Meter, letter, satellite_sockets

SUBTITLE = "Türksat Kanal Güncelleme Sistemi  ·  v%s  ·  %s" % (VERSION, HANDLE)


def artwork(image):
    return Pixmap() if Theme.image(image) else Label("")


class Page(Screen):
    KEY = ""
    BODY = ""

    def __init__(self, session, title, subtitle, keys=("", "", "", "")):
        self.skin = Theme.compose(self.KEY, self.body())
        Screen.__init__(self, session)
        self.skinName = "MSTKGS_%s_v4" % self.KEY
        self["t_title"] = Label(native(title))
        self["t_sub"] = Label(native(subtitle))
        for name, text in zip(("red", "green", "yellow", "blue"), keys):
            self["k_" + name] = Label(native(text))
        self._caption = native(title)
        self.onLayoutFinish.append(self._caption_apply)

    @classmethod
    def body(cls):
        return cls.BODY

    def _caption_apply(self):
        try:
            self.setTitle(self._caption)
        except Exception:
            pass

    def labels(self, *names):
        for name in names:
            self[name] = Label("")

    def buttons(self, *texts):
        for name, text in zip(("red", "green", "yellow", "blue"), texts):
            self["k_" + name].setText(native(text))

    def say(self, name, value):
        self[name].setText(native(value))

    def reveal(self, names, visible):
        for name in names:
            (self[name].show if visible else self[name].hide)()


TILES = (
    ("scan", "Oku ve Önizle", "Tabloyu oku, kanalları incele, sonra kur", "scan"),
    ("quick", "Tek Tuşla Kur", "Oku ve doğrudan güncelle", "bolt"),
    ("browse", "Kanal Gezgini", "Son okunan listeyi filtrele ve incele", "list"),
    ("signal", "Sinyal Testi", "Canlı kalite, güç ve dB ölçümü", "signal"),
    ("auto", "Otomatik Güncelleme", "Günlük, haftalık veya aylık kontrol", "clock"),
    ("vault", "Buket ve Yedekler", "Kaldır, geri yükle, temizle", "box"),
    ("setup", "Ayarlar", "Liste, numaralama, buket ve akış", "gear"),
    ("report", "Rapor ve Hakkında", "Son işlemin ayrıntılı dökümü", "doc"),
)
STAGES = ("Tuner hazırlanıyor", "Sinyale kilitleniliyor", "TKGS tablosu okunuyor", "Kanallar listeleniyor")
FEED_PACE = {"fast": 2.5, "normal": 4.5, "slow": 8.0}
FEED_ROW = 29
FEED_HEIGHT = 261


def _hub_body():
    T = Theme
    parts = ["""
        <widget name="h_over" position="64,122" size="600,22" font="Regular;14" foregroundColor="{CYAN}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="h_state" position="64,146" size="700,50" font="Regular;34" foregroundColor="{WHITE}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="h_meta" position="64,198" size="700,26" font="Regular;17" foregroundColor="{SOFT}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="h_auto" position="64,236" size="710,26" font="Regular;16" foregroundColor="{MUTED}" backgroundColor="{CARD}" transparent="1" valign="center" />"""]
    for i, (x, y) in enumerate(L.STATS):
        parts.append('<widget name="st_v%d" position="%d,%d" size="%d,52" font="Regular;38" foregroundColor="{WHITE}" '
                     'backgroundColor="{GLASS}" transparent="1" halign="center" valign="center" zPosition="1" />'
                     % (i, x, y + 26, L.STAT_W))
        parts.append('<widget name="st_l%d" position="%d,%d" size="%d,24" font="Regular;14" foregroundColor="{MUTED}" '
                     'backgroundColor="{GLASS}" transparent="1" halign="center" valign="center" zPosition="1" />'
                     % (i, x, y + 84, L.STAT_W))
    for i in range(len(TILES)):
        x, y = L.tile(i)
        parts.append(T.art("tile%d" % i, "tile", x, y, L.TILE_W, L.TILE_H, L.CARD, 1))
        parts.append(T.art("tico%d" % i, "b_" + TILES[i][3], x + 22, y + 22, 52, 52, L.CARD, 2))
        parts.append('<widget name="tnum%d" position="%d,%d" size="34,24" font="Regular;15" foregroundColor="{MUTED}" '
                     'backgroundColor="{CARD}" transparent="1" halign="right" valign="center" zPosition="2" />' % (i, x + 236, y + 20))
        parts.append('<widget name="ttl%d" position="%d,%d" size="250,30" font="Regular;21" foregroundColor="{TEXT}" '
                     'backgroundColor="{CARD}" transparent="1" valign="center" zPosition="2" />' % (i, x + 22, y + 88))
        parts.append('<widget name="tsub%d" position="%d,%d" size="250,40" font="Regular;15" foregroundColor="{MUTED}" '
                     'backgroundColor="{CARD}" transparent="1" zPosition="2" />' % (i, x + 22, y + 120))
    if T.image("ring"):
        x, y = L.tile(0)
        parts.append(T.art("ring", "ring", x, y, L.TILE_W, L.TILE_H, L.CARD, 3))
    bx, by, bw, bh = L.BUSY
    parts.append(T.art("busy", "busy", bx, by, bw, bh, L.CARD, 1))
    for i in range(4):
        parts.append(T.art("dot%d" % i, "dot_wait", 64, 366 + i * 38, 18, 18, L.LIFT, 2))
        parts.append('<widget name="sl%d" position="94,%d" size="300,30" font="Regular;19" foregroundColor="{MUTED}" '
                     'backgroundColor="{CARD}" transparent="1" valign="center" zPosition="2" />' % (i, 360 + i * 38))
    parts.append("""
        <widget name="b_title" position="64,312" size="520,36" font="Regular;24" foregroundColor="{WHITE}" backgroundColor="{CARD}" transparent="1" valign="center" zPosition="2" />
        <widget name="p_pct" position="400,352" size="200,74" font="Regular;56" foregroundColor="{CYAN}" backgroundColor="{CARD}" transparent="1" halign="right" valign="center" zPosition="2" />
        <widget name="p_bar" position="64,522" size="536,6" foregroundColor="{CYAN}" backgroundColor="{LIFT}" borderWidth="0" zPosition="2" />
        <widget name="p_text" position="64,532" size="536,28" font="Regular;16" foregroundColor="{SOFT}" backgroundColor="{CARD}" transparent="1" valign="center" zPosition="2" />
        <widget name="m_ql" position="64,568" size="84,26" font="Regular;16" foregroundColor="{MUTED}" backgroundColor="{CARD}" transparent="1" valign="center" zPosition="2" />
        <widget name="m_q" position="150,578" size="330,6" foregroundColor="{GREEN}" backgroundColor="{LIFT}" borderWidth="0" zPosition="2" />
        <widget name="m_qv" position="486,568" size="114,26" font="Regular;16" foregroundColor="{TEXT}" backgroundColor="{CARD}" transparent="1" halign="right" valign="center" zPosition="2" />
        <widget name="m_pl" position="64,600" size="84,26" font="Regular;16" foregroundColor="{MUTED}" backgroundColor="{CARD}" transparent="1" valign="center" zPosition="2" />
        <widget name="m_p" position="150,610" size="330,6" foregroundColor="{BLUE}" backgroundColor="{LIFT}" borderWidth="0" zPosition="2" />
        <widget name="m_pv" position="486,600" size="114,26" font="Regular;16" foregroundColor="{TEXT}" backgroundColor="{CARD}" transparent="1" halign="right" valign="center" zPosition="2" />
        <widget name="f_head" position="648,326" size="300,28" font="Regular;14" foregroundColor="{CYAN}" backgroundColor="{WELL}" transparent="1" valign="center" zPosition="2" />
        <widget name="f_count" position="900,326" size="300,28" font="Regular;15" foregroundColor="{SOFT}" backgroundColor="{WELL}" transparent="1" halign="right" valign="center" zPosition="2" />
        <widget name="feed" position="636,360" size="576,261" backgroundColor="{WELL}" backgroundColorSelected="{WELL}" foregroundColor="{TEXT}" scrollbarMode="showNever" zPosition="2" />""")
    return "".join(parts)


class ControlDeck(Page):
    KEY = "main"
    IDLE_KEYS = ("Çıkış", "Oku ve Önizle", "Ayarlar", "Otomatik")

    @classmethod
    def body(cls):
        return _hub_body()

    def __init__(self, session, *rest):
        Page.__init__(self, session, NAME, SUBTITLE, self.IDLE_KEYS)
        self.labels("h_over", "h_state", "h_meta", "h_auto", "b_title", "p_pct", "p_text",
                    "m_ql", "m_qv", "m_pl", "m_pv", "f_head", "f_count")
        for i in range(3):
            self.labels("st_v%d" % i, "st_l%d" % i)
        self.tile_parts = []
        for i, (_, title, sub, icon) in enumerate(TILES):
            self["tile%d" % i] = artwork("tile")
            self["tico%d" % i] = artwork("b_" + icon)
            self.labels("tnum%d" % i, "ttl%d" % i, "tsub%d" % i)
            self.tile_parts += ["tile%d" % i, "tico%d" % i, "tnum%d" % i, "ttl%d" % i, "tsub%d" % i]
        self.has_ring = bool(Theme.image("ring"))
        if self.has_ring:
            self["ring"] = Pixmap()
            self.tile_parts.append("ring")
        self["busy"] = artwork("busy")
        self.busy_parts = ["busy", "b_title", "p_pct", "p_bar", "p_text", "m_ql", "m_q", "m_qv", "m_pl", "m_p",
                           "m_pv", "f_head", "f_count", "feed"]
        for i in range(4):
            self["dot%d" % i] = artwork("dot_wait")
            self.labels("sl%d" % i)
            self.busy_parts += ["dot%d" % i, "sl%d" % i]
        for name in ("p_bar", "m_q", "m_p"):
            self[name] = ProgressBar()
        self["feed"] = listbox((18, 14), FEED_ROW)
        actions = {
            "ok": self.press_ok, "cancel": self.press_exit, "red": self.press_exit,
            "green": self.press_green, "yellow": lambda: self.open_key("setup"),
            "blue": lambda: self.open_key("auto"), "menu": lambda: self.open_key("setup"),
            "left": lambda: self.shift(-1), "right": lambda: self.shift(1),
            "up": lambda: self.shift(-4), "down": lambda: self.shift(4),
        }
        for n in range(1, len(TILES) + 1):
            actions[str(n)] = (lambda i: lambda: self.jump(i))(n - 1)
        self["remote"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions",
                                     "NumberActions"], actions, -1)
        self.reader = engine.Reader(session, self.on_step, self.on_end)
        self.cursor = 0
        self.mode = None
        self.result = None
        self.stage = 0
        self.stream = []
        self.fed = 0
        self.batch = 1
        self.after = None
        self.genres = {}
        self.depth = 8
        self.pump = engine.ticker(self._pump)
        self.pause = engine.ticker(self._after_feed)
        self.clocktick = engine.ticker(self.refresh)
        self.onLayoutFinish.append(self._build)
        self.onClose.append(self._teardown)

    @property
    def streaming(self):
        return self.after is not None

    @property
    def working(self):
        return self.reader.busy or self.streaming

    def _build(self):
        note("arayuz", "ana ekran acildi", genislik=Theme.px(L.W), gorsel="tam" if Theme.rich() else "duz")
        shape_list(self["feed"], (18, 14), FEED_ROW)
        try:
            self["feed"].instance.setSelectionEnable(0)
        except Exception:
            pass
        self.depth = self._feed_depth()
        for i, (_, title, sub, _) in enumerate(TILES):
            self.say("tnum%d" % i, str(i + 1))
            self.say("ttl%d" % i, title)
            self.say("tsub%d" % i, sub)
        for i, caption in enumerate(("TV", "RADYO", "42.0E TUNER")):
            self.say("st_l%d" % i, caption)
        self.say("h_over", "KANAL LİSTESİ")
        self.say("f_head", "BULUNAN KANALLAR")
        self.reveal(self.busy_parts, False)
        self._focus(0)
        self.refresh()
        self.clocktick.start(30000, False)

    def _focus(self, index):
        old, self.cursor = self.cursor, index
        for i in (old, index):
            active = i == index
            paint(self["ttl%d" % i], L.WHITE if active else L.TEXT)
            if not self.has_ring:
                paint(self["tile%d" % i], back=L.LIFT if active else L.CARD)
            self.say("ttl%d" % i, TILES[i][1])
        if self.has_ring:
            x, y = L.tile(index)
            try:
                self["ring"].instance.move(ePoint(Theme.px(x), Theme.px(y)))
            except Exception:
                pass

    def shift(self, delta):
        if not self.working:
            self._focus((self.cursor + delta) % len(TILES))

    def jump(self, index):
        if not self.working:
            self._focus(index)
            self.open_key(TILES[index][0])

    def refresh(self):
        if self.working:
            return
        mem = engine.Memory.read()
        tuners = satellite_sockets()
        if mem.get("install_time"):
            self.say("h_state", "%s TV  ·  %s radyo kanalı" % (mem.get("tv", 0), mem.get("radio", 0)))
            meta = ["Son kurulum %s" % engine.stamp(mem["install_time"])]
            if mem.get("list"):
                meta.append("%s listesi" % native(mem["list"]))
            if mem.get("version"):
                meta.append("TKGS v%s" % native(mem["version"]))
            if mem.get("title"):
                meta.append(native(mem["title"]))
            self.say("h_meta", "  ·  ".join(meta))
        else:
            self.say("h_state", "Henüz kurulum yapılmadı")
            self.say("h_meta", "Oku ve Önizle ile Türksat TKGS listesini birkaç saniyede kurun.")
        self.say("h_auto", auto.status_line())
        self.say("st_v0", native(u"%s" % mem.get("tv", "-")) if mem.get("install_time") else "-")
        self.say("st_v1", native(u"%s" % mem.get("radio", "-")) if mem.get("install_time") else "-")
        self.say("st_v2", ",".join(letter(s) for s in tuners) if tuners else "YOK")
        paint(self["st_v2"], L.WHITE if tuners else L.RED)

    def press_ok(self):
        if self.streaming:
            return self._flush()
        if not self.working:
            self.open_key(TILES[self.cursor][0])

    def press_green(self):
        if self.streaming:
            return self._flush()
        self.open_key("scan")

    def press_exit(self):
        if self.reader.busy:
            self.reader.abort()
            self._idle()
            return self.session.open(MessageBox, "İşlem iptal edildi. İzlenen kanal geri yüklendi.",
                                     MessageBox.TYPE_INFO, timeout=4)
        if self.streaming:
            self.pump.stop()
            self.pause.stop()
            self.stream, self.after = [], None
            return self._idle()
        self.close()

    def open_key(self, key):
        if self.working:
            return
        target = {"signal": SignalDeck, "vault": ArchiveDeck, "setup": PrefsDeck, "auto": TimerDeck}.get(key)
        if key in ("scan", "quick"):
            self.begin(key)
        elif key == "browse":
            self.browse_cached()
        elif key == "report":
            self.session.open(LogDeck)
        elif target is not None:
            self.session.openWithCallback(lambda *a: self.refresh(), target)

    def begin(self, mode):
        if not satellite_sockets():
            return self.session.open(MessageBox, "42.0E uydusu atanmış bir uydu tuneri yok.\n"
                                     "Lütfen önce tuner ayarlarına Türksat 42.0E uydusunu ekleyin.", MessageBox.TYPE_ERROR)
        if engine.GATE["owner"] not in (None, "hub"):
            return self.session.open(MessageBox, "Arka planda otomatik güncelleme sürüyor. Birkaç saniye sonra tekrar deneyin.",
                                     MessageBox.TYPE_INFO, timeout=5)
        try:
            recording = bool(self.session.nav.getRecordings())
        except Exception:
            recording = False
        if recording:
            return self.session.openWithCallback(
                lambda yes: yes and self._launch(mode), MessageBox,
                "Şu anda bir kayıt yapılıyor.\nTKGS okuması bir tuner kullanacak; yine de başlatılsın mı?",
                MessageBox.TYPE_YESNO, default=False)
        self._launch(mode)

    def _launch(self, mode):
        if not engine.claim("hub"):
            return
        self.mode = mode
        self.stage = 0
        self.say("b_title", "Tek tuşla kurulum" if mode == "quick" else "TKGS okunuyor")
        for i, name in enumerate(STAGES):
            swap(self["dot%d" % i], "dot_wait", L.LIFT)
            paint(self["sl%d" % i], L.MUTED)
            self.say("sl%d" % i, name)
        for name in ("p_bar", "m_q", "m_p"):
            self[name].setValue(0)
        for name, value in (("m_ql", "Kalite"), ("m_pl", "Güç"), ("m_qv", "-"), ("m_pv", "-"),
                            ("p_pct", "0%"), ("p_text", ""), ("f_count", "")):
            self.say(name, value)
        self["feed"].setList([])
        self.buttons("İptal", "", "", "")
        self.reveal(self.tile_parts, False)
        self.reveal(self.busy_parts, True)
        self.reader.start()

    def _idle(self):
        engine.release("hub")
        self.buttons(*self.IDLE_KEYS)
        self.reveal(self.busy_parts, False)
        self.reveal(self.tile_parts, True)
        self._focus(self.cursor)
        self.refresh()

    def _stage(self, stage):
        if stage == self.stage:
            return
        for i in range(4):
            done, live = i + 1 < stage, i + 1 == stage
            swap(self["dot%d" % i], "dot_done" if done else ("dot_on" if live else "dot_wait"),
                 L.GREEN if done else (L.CYAN if live else L.LIFT))
            paint(self["sl%d" % i], L.TEXT if done else (L.WHITE if live else L.MUTED))
            self.say("sl%d" % i, STAGES[i])
        self.stage = stage

    def on_step(self, stage, message, percent, meter):
        if stage:
            self._stage(stage)
        if message is not None:
            self.say("p_text", message)
        if percent is not None:
            self["p_bar"].setValue(int(percent))
            self.say("p_pct", "%d%%" % int(percent))
        if meter is not None:
            if meter.quality is not None:
                self["m_q"].setValue(meter.quality)
                self.say("m_qv", "%d%%%s" % (meter.quality, (" · %.1f dB" % meter.db) if meter.db else ""))
            if meter.power is not None:
                self["m_p"].setValue(meter.power)
                self.say("m_pv", "%d%%" % meter.power)

    def on_end(self, result, error):
        if error:
            self._idle()
            return self.session.open(MessageBox, native(error), MessageBox.TYPE_ERROR)
        self.result = result
        try:
            plan = result.blueprint()
        except Exception as exc:
            self._idle()
            return self.session.open(MessageBox, "lamedb okunamadı: %s" % native(str(exc)), MessageBox.TYPE_ERROR)
        engine.write_report(result, plan)
        self._stream(result, plan)

    def _stream(self, result, plan):
        order = result.order
        rows = list(plan.walk(order, radio=False)) + list(plan.walk(order, radio=True))
        pace = FEED_PACE.get(opts.feed.value)
        self.after = (result, plan)
        self.genres = result.catalog.genres
        if not rows or pace is None:
            self.stream = []
            return self._after_feed()
        self.stream = rows
        self.fed = 0
        self.batch = max(1, int(math.ceil(len(rows) * 0.02 / pace)))
        self.buttons("Durdur", "Atla", "", "")
        self._stage(4)
        paint(self["p_bar"], L.GREEN)
        self.pump.start(20, False)

    def _feed_row(self, pos, link, newest):
        prog = link.program
        tone = L.CYAN if newest else L.TEXT
        row = [link]
        if newest:
            row.append(cell(0, 2, 576, FEED_ROW - 4, "", back=0x0f2236, back_chosen=0x0f2236))
            row.append(cell(0, 6, 3, FEED_ROW - 12, "", back=L.CYAN, back_chosen=L.CYAN))
        row += [cell(6, 0, 46, FEED_ROW, "%d" % pos, font=1, fore=L.MUTED, chosen=L.MUTED, align=RIGHT),
                cell(66, 0, 300, FEED_ROW, prog.name or u"SID %d" % prog.svc_id, fore=tone, chosen=tone),
                cell(372, 0, 128, FEED_ROW, u"Radyo" if prog.radio else self.genres.get(prog.genre_id, u""),
                     font=1, fore=L.MUTED, chosen=L.MUTED)]
        if link.fresh:
            row.append(cell(506, 5, 62, 19, "YENİ", font=1, fore=L.GREEN, chosen=L.GREEN, align=CENTER, back=0x10301f,
                            back_chosen=0x10301f))
        return row

    def _feed_depth(self):
        row = max(1, Theme.px(FEED_ROW))
        try:
            height = self["feed"].instance.size().height()
        except Exception:
            height = 0
        return max(1, (height or Theme.px(FEED_HEIGHT)) // row)

    def _pump(self):
        total = len(self.stream)
        if not total:
            return self.pump.stop()
        self.fed = min(total, self.fed + self.batch)
        window = self.stream[max(0, self.fed - self.depth):self.fed]
        self["feed"].setList([self._feed_row(pos, link, i == len(window) - 1) for i, (pos, link) in enumerate(window)])
        try:
            self["feed"].moveToIndex(0)
        except Exception:
            pass
        self.say("p_text", window[-1][1].program.name)
        self.say("f_count", "%d / %d" % (self.fed, total))
        self["p_bar"].setValue(self.fed * 100 // total)
        self.say("p_pct", "%d%%" % (self.fed * 100 // total))
        if self.fed >= total:
            self.pump.stop()
            self.pause.start(800, True)

    def _flush(self):
        self.fed = max(0, len(self.stream) - self.batch)
        self._pump()

    def _after_feed(self):
        self.pause.stop()
        paint(self["p_bar"], L.CYAN)
        if self.after is None:
            return
        result, plan = self.after
        self.stream, self.after = [], None
        if self.mode == "quick":
            return self._install(result, plan)
        self._idle()
        self.session.openWithCallback(lambda answer=None: self._from_browser(answer, result), ChannelDeck, result, plan)

    def browse_cached(self):
        result = self.result
        if result is None:
            try:
                result = engine.Outcome.cached()
            except Exception as exc:
                return self.session.open(MessageBox, "Kayıtlı TKGS verisi çözülemedi: %s" % native(str(exc)),
                                         MessageBox.TYPE_ERROR)
        if result is None:
            return self.session.openWithCallback(lambda yes: yes and self.begin("scan"), MessageBox,
                                                 "Henüz okunmuş bir TKGS listesi yok.\nŞimdi TKGS yayınından okunsun mu?",
                                                 MessageBox.TYPE_YESNO)
        plan = result.blueprint()
        engine.write_report(result, plan)
        self.session.openWithCallback(lambda answer=None: self._from_browser(answer, result), ChannelDeck, result, plan)

    def _from_browser(self, answer, result):
        if answer == "apply":
            return self._install(result, result.blueprint())
        self.refresh()

    def _install(self, result, plan):
        if not plan.links:
            self._idle()
            return self.session.open(MessageBox, "TKGS listesinde kurulabilecek kanal bulunamadı.", MessageBox.TYPE_ERROR)
        ok, message = engine.install(result, plan)
        self._idle()
        self.session.open(MessageBox, native(message), MessageBox.TYPE_INFO if ok else MessageBox.TYPE_ERROR,
                          timeout=20 if ok else 0)

    def _teardown(self):
        self.pump.stop()
        self.pause.stop()
        self.clocktick.stop()
        self.reader.abort()
        engine.release("hub")


class ChannelDeck(Page):
    KEY = "browser"
    MODES = ("TÜMÜ", "TV", "RADYO")

    @classmethod
    def body(cls):
        parts = []
        for i in range(3):
            x = 40 + i * 132
            parts.append(Theme.art("cbg%d" % i, "chip_off", x, 110, 120, 36, L.CARD, 1))
            parts.append('<widget name="chip%d" position="%d,110" size="120,36" font="Regular;17" foregroundColor="{MUTED}" '
                         'backgroundColor="{CARD}" transparent="1" halign="center" valign="center" zPosition="2" />' % (i, x))
        parts.append("""
        <widget name="genre" position="640,110" size="600,36" font="Regular;19" foregroundColor="{TEXT}" backgroundColor="{INK}" transparent="1" halign="right" valign="center" />
        <eLabel text="NO" position="44,156" size="64,42" font="Regular;14" foregroundColor="{MUTED}" backgroundColor="{LIFT}" transparent="1" halign="right" valign="center" />
        <eLabel text="KANAL" position="132,156" size="460,42" font="Regular;14" foregroundColor="{MUTED}" backgroundColor="{LIFT}" transparent="1" valign="center" />
        <eLabel text="KATEGORİ" position="644,156" size="220,42" font="Regular;14" foregroundColor="{MUTED}" backgroundColor="{LIFT}" transparent="1" valign="center" />
        <eLabel text="DURUM" position="904,156" size="300,42" font="Regular;14" foregroundColor="{MUTED}" backgroundColor="{LIFT}" transparent="1" valign="center" />
        <widget name="rows" position="44,202" size="1192,390" backgroundColor="{CARD}" backgroundColorSelected="{CARD}" foregroundColor="{TEXT}" scrollbarMode="showOnDemand" />
        <widget name="summary" position="56,614" size="860,34" font="Regular;17" foregroundColor="{TEXT}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="count" position="920,614" size="312,34" font="Regular;17" foregroundColor="{CYAN}" backgroundColor="{CARD}" transparent="1" halign="right" valign="center" />""")
        return "".join(parts)

    def __init__(self, session, result, plan):
        cat = result.catalog
        Page.__init__(self, session, "Kanal Gezgini",
                      "%s  ·  %s listesi  ·  TKGS v%s" % (native(cat.headline or "TKGS"), native(result.order),
                                                          native(result.version)),
                      ("Kapat", "Kanal Listesini Kur" if plan.links else "", "Kategori", "TV / Radyo"))
        self.result, self.plan, self.cat = result, plan, cat
        self["rows"] = listbox((20, 15), 39)
        self.labels("chip0", "chip1", "chip2", "genre", "summary", "count")
        for i in range(3):
            self["cbg%d" % i] = artwork("chip_off")
        self.mode = 0
        self.genres = [None] + sorted(set(l.program.genre_id for l in plan.links
                                          if not l.radio and l.program.genre_id in cat.genres))
        self.genre = 0
        tv = sum(1 for l in plan.links if not l.radio)
        parts = ["%d TV" % tv, "%d radyo" % (len(plan.links) - tv), "%d yeni kanal" % plan.tally(True)]
        if plan.add_muxes:
            parts.append("%d yeni TP" % len(plan.add_muxes))
        if plan.fix_muxes:
            parts.append("%d TP güncellenecek" % len(plan.fix_muxes))
        change = engine.delta(plan, result.order)
        if change is not None:
            parts.append("mevcut bukete göre +%d / -%d" % change)
        self.digest = "  ·  ".join(parts)
        self["remote"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "ChannelSelectBaseActions"], {
            "ok": self.details, "cancel": lambda: self.close(None), "red": lambda: self.close(None),
            "green": self.confirm, "yellow": self.next_genre, "blue": self.next_mode,
            "up": lambda: step(self["rows"], "moveUp"), "down": lambda: step(self["rows"], "moveDown"),
            "left": lambda: step(self["rows"], "pageUp"), "right": lambda: step(self["rows"], "pageDown"),
            "nextBouquet": lambda: step(self["rows"], "pageUp"), "prevBouquet": lambda: step(self["rows"], "pageDown"),
        }, -1)
        self.onLayoutFinish.append(self.render)

    def _row(self, index, pos, link, skip):
        prog = link.program
        out = prog.encrypted and skip
        stripe = L.CARD if index % 2 == 0 else 0x0d1422
        row = [link,
               cell(0, 1, 1192, 37, "", back=stripe, back_chosen=0x18304d),
               cell(0, 8, 4, 23, "", back=stripe, back_chosen=L.CYAN),
               cell(0, 0, 64, 39, "%d" % pos, fore=L.MUTED, chosen=L.CYAN, align=RIGHT),
               cell(88, 0, 500, 39, prog.name or u"SID %d" % prog.svc_id,
                    fore=L.MUTED if out else L.TEXT, chosen=L.MUTED if out else L.WHITE),
               cell(600, 0, 250, 39, u"Radyo" if prog.radio else self.cat.genres.get(prog.genre_id, u""),
                    font=1, fore=L.MUTED, chosen=L.SOFT)]
        if prog.hd:
            row.append(cell(860, 9, 50, 21, "HD", font=1, fore=L.CYAN, chosen=L.CYAN, align=CENTER, back=0x0d3140))
        if link.fresh:
            row.append(cell(918, 9, 70, 21, "YENİ", font=1, fore=L.GREEN, chosen=L.GREEN, align=CENTER, back=0x10301f))
        if prog.encrypted:
            row.append(cell(996, 9, 90, 21, "HARİÇ" if out else "ŞİFRELİ", font=1,
                            fore=L.RED if out else L.AMBER, chosen=L.RED if out else L.AMBER,
                            align=CENTER, back=0x3a2410))
        return row

    def render(self):
        shape_list(self["rows"], (20, 15), 39)
        skip = not opts.scrambled.value
        genre = self.genres[self.genre]
        order = self.result.order
        picks = []
        for wants_radio in (False, True):
            if (self.mode == 1 and wants_radio) or (self.mode == 2 and not wants_radio):
                continue
            picks += list(self.plan.walk(order, radio=wants_radio, category=genre if not wants_radio else None))
            if genre is not None:
                break
        self["rows"].setList([self._row(i, pos, link, skip) for i, (pos, link) in enumerate(picks)])
        for i, name in enumerate(self.MODES):
            active = i == self.mode
            swap(self["cbg%d" % i], "chip_on" if active else "chip_off", L.CYAN if active else L.CARD)
            paint(self["chip%d" % i], L.INK if active else L.SOFT)
            self.say("chip%d" % i, name)
        self.say("genre", u"Kategori:  %s" % (self.cat.genres.get(genre, u"?") if genre is not None else u"Tümü"))
        self.say("summary", self.digest)
        self.say("count", "%d kanal" % len(picks))

    def next_mode(self):
        self.mode = (self.mode + 1) % 3
        if self.mode == 2:
            self.genre = 0
        self.render()

    def next_genre(self):
        if len(self.genres) < 2:
            return
        self.genre = (self.genre + 1) % len(self.genres)
        if self.genres[self.genre] is not None and self.mode == 2:
            self.mode = 0
        self.render()

    def confirm(self):
        if self.plan.links:
            self.session.openWithCallback(lambda yes: yes and self.close("apply"), MessageBox,
                                          native("%s\n\nKanal listesi kurulsun mu?" % self.digest), MessageBox.TYPE_YESNO)

    def details(self):
        cur = self["rows"].getCurrent()
        if not cur:
            return
        link = cur[0]
        prog = link.program
        kind = "Radyo" if prog.radio else ("HD TV" if prog.hd else "SD TV")
        self.session.open(MessageBox, native(
            u"%s\n\nTKGS no: %d   ·   SID: %d   ·   Tür: %s (0x%02X)\nYayıncı: %s\nKategori: %s\nTransponder: %s\n"
            u"Durum: %s%s\n\n%s" % (
                prog.name, prog.chno, prog.svc_id, uni(kind), prog.kind or 0, prog.brand or u"-",
                self.cat.genres.get(prog.genre_id, u"-"), uni(prog.carrier.label()),
                u"yeni eklenecek" if link.fresh else u"listede var", u"  ·  şifreli" if prog.encrypted else u"",
                uni(link.service.reference))), MessageBox.TYPE_INFO)


class SignalDeck(Page):
    KEY = "signal"
    BODY = """
        <widget name="freq" position="64,124" size="760,46" font="Regular;34" foregroundColor="{WHITE}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="slot" position="64,172" size="760,28" font="Regular;18" foregroundColor="{SOFT}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="lock" position="64,210" size="760,90" font="Regular;64" foregroundColor="{MUTED}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="db" position="840,180" size="370,110" font="Regular;72" foregroundColor="{WHITE}" backgroundColor="{CARD}" transparent="1" halign="right" valign="center" />
        <widget name="dbl" position="840,124" size="370,30" font="Regular;15" foregroundColor="{CYAN}" backgroundColor="{CARD}" transparent="1" halign="right" valign="center" />
        <widget name="ql" position="88,368" size="400,30" font="Regular;18" foregroundColor="{SOFT}" backgroundColor="{WELL}" transparent="1" valign="center" />
        <widget name="qv" position="792,364" size="400,36" font="Regular;28" foregroundColor="{WHITE}" backgroundColor="{WELL}" transparent="1" halign="right" valign="center" />
        <widget name="q" position="88,406" size="1104,14" foregroundColor="{GREEN}" backgroundColor="{LIFT}" borderWidth="0" />
        <widget name="pl" position="88,452" size="400,30" font="Regular;18" foregroundColor="{SOFT}" backgroundColor="{WELL}" transparent="1" valign="center" />
        <widget name="pv" position="792,448" size="400,36" font="Regular;28" foregroundColor="{WHITE}" backgroundColor="{WELL}" transparent="1" halign="right" valign="center" />
        <widget name="p" position="88,490" size="1104,14" foregroundColor="{BLUE}" backgroundColor="{LIFT}" borderWidth="0" />
        <widget name="hint" position="64,562" size="1152,72" font="Regular;17" foregroundColor="{MUTED}" backgroundColor="{CARD}" transparent="1" />"""

    def __init__(self, session, *rest):
        Page.__init__(self, session, "Sinyal Testi", "Türksat 42.0E  ·  TKGS transponderı  ·  ham tuner ile canlı ölçüm",
                      ("Kapat", "Sonraki Frekans", "", ""))
        self.labels("freq", "slot", "lock", "db", "dbl", "ql", "qv", "pl", "pv", "hint")
        self["q"] = ProgressBar()
        self["p"] = ProgressBar()
        self["remote"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "cancel": self.close, "red": self.close, "ok": self.close, "green": self.hop}, -1)
        self.combos = [(b, mode) for b in BEACONS for mode in ("s", "s2")]
        self.at = 0
        self.front = None
        self.halted = False
        self.prior = None
        self.locked = False
        self.since = 0.0
        self.poller = engine.ticker(self._sample)
        self.onLayoutFinish.append(self._open)
        self.onClose.append(self._shut)

    def _status(self, text, color):
        paint(self["lock"], color)
        self.say("lock", text)

    def _open(self):
        for name, value in (("ql", "Sinyal kalitesi"), ("pl", "Sinyal gücü"), ("qv", "-"), ("pv", "-"), ("db", "-"),
                            ("dbl", "SNR"),
                            ("hint", "Kilit yoksa DVB-S ve DVB-S2 sırayla otomatik denenir. Yeşil: frekansı elle değiştir. "
                                     "Kanal listesi değiştirilmez; çıkışta izlenen kanal geri yüklenir.")):
            self.say(name, value)
        candidates = satellite_sockets()
        if not candidates:
            return self._status("42.0E tuner yok", L.RED)
        nav = self.session.nav
        self.prior = (getattr(nav, "getCurrentlyPlayingServiceOrGroup", None) or nav.getCurrentlyPlayingServiceReference)()
        if engine.GATE["owner"] not in (None,):
            return self._status("Tuner meşgul", L.AMBER)
        self.front = Frontend.grab(candidates)
        if self.front is None:
            nav.stopService()
            self.halted = True
            time.sleep(0.35)
            self.front = Frontend.grab(candidates)
        if self.front is None:
            return self._status("Tuner ayrılamadı", L.RED)
        self._tune()
        self.poller.start(400, False)

    def _tune(self):
        (freq, pol, sr), mode = self.combos[self.at]
        self.say("freq", "%d %s %d" % (freq, pol, sr))
        self.say("slot", "%s  ·  Tuner %s  ·  42.0E" % ("DVB-S2" if mode == "s2" else "DVB-S", letter(self.front.socket)))
        self._status("Kilitleniyor...", L.AMBER)
        self.locked = False
        self.since = clock()
        try:
            self.front.aim(freq, pol, sr, mode)
        except Exception as exc:
            self.say("lock", "Hata: %s" % exc)

    def hop(self):
        if self.front is not None:
            self.at = (self.at + 2 - self.at % 2) % len(self.combos)
            self._tune()

    def _sample(self):
        m = Meter.read(self.front.readout()) if self.front is not None else None
        if m is None:
            return
        if m.locked and not self.locked:
            self.locked = True
            self._status("KİLİTLİ", L.GREEN)
            (freq, pol, sr), mode = self.combos[self.at]
            note("sinyal", "%d %s %d %s kilitli" % (freq, pol, sr, mode), kalite=m.quality, guc=m.power, snr_db=m.db,
                 sure="%.1f" % (clock() - self.since))
        elif not m.locked and self.locked:
            self.locked = False
            self.since = clock()
            self._status("Kilit kaybedildi", L.RED)
        elif not m.locked and clock() - self.since > 4.0:
            (freq, pol, sr), mode = self.combos[self.at]
            note("sinyal", "%d %s %d %s kilit yok" % (freq, pol, sr, mode), kalite=m.quality, guc=m.power)
            self.at = (self.at + 1) % len(self.combos)
            return self._tune()
        if m.quality is not None:
            self["q"].setValue(m.quality)
            self.say("qv", "%d%%" % m.quality)
        if m.power is not None:
            self["p"].setValue(m.power)
            self.say("pv", "%d%%" % m.power)
        self.say("db", "%.1f dB" % m.db if m.db else "-")

    def _shut(self):
        self.poller.stop()
        if self.front is not None:
            self.front.release()
            self.front = None
        if self.prior is not None and self.halted:
            try:
                self.session.nav.playService(self.prior)
            except Exception:
                pass


def _action_row(span, key, title, hint, icon, number):
    art = picture(22, 24, L.ICON, L.ICON, icon) if Theme.rich() else None
    row = [key]
    if art is not None:
        row.append(art)
    else:
        row.append(cell(0, 10, 5, 56, "", back=L.CARD, back_chosen=L.CYAN))
        row.append(cell(14, 0, 40, 76, "%02d" % number, fore=L.MUTED, chosen=L.CYAN))
    row.append(cell(66, 12, span - 76, 30, title))
    row.append(cell(66, 42, span - 76, 24, hint, font=1, fore=L.MUTED, chosen=L.SOFT))
    return row


class ArchiveDeck(Page):
    KEY = "manage"
    BODY = """
        <widget name="menu" position="44,116" size="536,520" backgroundColor="{CARD}" {SEL:manage} foregroundColor="{TEXT}" foregroundColorSelected="{WHITE}" scrollbarMode="showNever" />
        <widget name="i_title" position="632,118" size="592,42" font="Regular;27" foregroundColor="{WHITE}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="i_text" position="632,186" size="592,440" font="Regular;18" foregroundColor="{SOFT}" backgroundColor="{CARD}" transparent="1" />"""

    ACTIONS = (
        ("remove", "TKGS buketlerini kaldır", "TV, radyo ve kategori buketleri silinir", "trash"),
        ("restore", "Yedekten geri yükle", "Kurulum öncesi kanal listesine dön", "undo"),
        ("purge", "Yedekleri temizle", "Yedek setini sil", "erase"),
        ("reload", "Kanal listesini yenile", "lamedb ve buketleri yeniden yükle", "refresh"),
        ("cache", "Kayıtlı ham veriyi sil", "Kanal gezgini önbelleğini temizle", "disk"),
    )
    ASK = {
        "remove": "Tüm TKGS buketleri kaldırılsın mı?\nÖnce mevcut liste yedeklenir.",
        "restore": "Kanal listesi yedekten geri yüklensin mi?\nMevcut liste değişecek.",
        "purge": "Yedek seti silinsin mi?\nBu işlemden sonra geri yükleme yapılamaz.",
        "cache": "Kayıtlı ham TKGS verisi silinsin mi?",
    }

    def __init__(self, session, *rest):
        Page.__init__(self, session, "Buket ve Yedekler", "TKGS buketleri  ·  yedek seti  ·  önbellek",
                      ("Kapat", "Uygula", "", ""))
        self.vault = store.Vault(engine.FOLDER, engine.PREFIX)
        self["menu"] = listbox((22, 16), L.ROW["manage"])
        self.labels("i_title", "i_text")
        self["remote"] = ActionMap(["DirectionActions", "ColorActions", "OkCancelActions"], {
            "ok": self.execute, "green": self.execute, "cancel": self.close, "red": self.close,
            "up": lambda: self._move("moveUp"), "down": lambda: self._move("moveDown")}, -1)
        self.onLayoutFinish.append(self._build)

    def _build(self):
        shape_list(self["menu"], (22, 16), L.ROW["manage"])
        self["menu"].setList([_action_row(536, key, title, hint, "i_" + icon, i + 1)
                              for i, (key, title, hint, icon) in enumerate(self.ACTIONS)])
        self.explain_action()

    def _move(self, how):
        step(self["menu"], how)
        self.explain_action()

    def chosen(self):
        cur = self["menu"].getCurrent()
        return cur[0] if cur else self.ACTIONS[0][0]

    def explain_action(self):
        key = self.chosen()
        self.say("i_title", dict((a[0], a[1]) for a in self.ACTIONS)[key])
        if key == "remove":
            names = sorted(n for n in os.listdir(engine.FOLDER) if n.startswith(engine.PREFIX)
                           and n.endswith((".tv", ".radio"))) if os.path.isdir(engine.FOLDER) else []
            body = ("Kaldırılacak buketler:\n\n" + "\n".join(names)) if names else "Kurulu TKGS buketi yok."
            body += "\n\nlamedb'deki kanallar silinmez; yalnızca buketler ve indeks satırları kaldırılır."
        elif key in ("restore", "purge"):
            held = self.vault.items()
            body = ("Yedek seti:\n\n" + "\n".join("%s   ·   %s" % (native(n), engine.stamp(t)) for n, t in held)
                    if held else "Yedek bulunamadı.")
        elif key == "reload":
            body = "lamedb ve tüm buketler Enigma2 tarafından diskteki hâliyle yeniden yüklenir."
        else:
            files = [p for p in (engine.RAW_KEEP, engine.RAW_TMP) if os.path.exists(p)]
            body = ("Önbellek dosyaları:\n\n" + "\n".join(files)) if files else "Kayıtlı ham TKGS verisi yok."
        self.say("i_text", body)

    def execute(self):
        key = self.chosen()
        if key == "reload":
            engine.reload_lists(True)
            return self.session.open(MessageBox, "Kanal listesi yeniden yüklendi.", MessageBox.TYPE_INFO, timeout=4)
        self.session.openWithCallback(lambda yes: yes and self._do(key), MessageBox, self.ASK[key],
                                      MessageBox.TYPE_YESNO, default=False)

    def _do(self, key):
        if key == "remove":
            self.vault.capture()
            count = store.strip_owned(engine.FOLDER, engine.PREFIX)
            engine.reload_lists()
            engine.Memory.forget_install()
            message = "%d TKGS buketi kaldırıldı." % count
        elif key == "restore":
            count = self.vault.restore()
            engine.reload_lists(True)
            engine.Memory.forget_install()
            message = "%d dosya yedekten geri yüklendi." % count
        elif key == "purge":
            message = "%d yedek silindi." % self.vault.wipe()
        else:
            count = 0
            for path in (engine.RAW_KEEP, engine.RAW_TMP):
                try:
                    os.remove(path)
                    count += 1
                except OSError:
                    pass
            message = "%d önbellek dosyası silindi." % count
        self.explain_action()
        self.session.open(MessageBox, message, MessageBox.TYPE_INFO, timeout=5)


class _Form(ConfigListScreen, Page):
    FIELDS = ()

    def _entries(self):
        return [(label, attr, note) for label, attr, note in self.FIELDS]

    def _mount(self):
        self.fed = self._entries()
        self.notes = [note for _, _, note in self.fed]
        return [getConfigListEntry(native(label), getattr(opts, attr)) for label, attr, _ in self.fed]

    def _remount(self):
        entries = self._mount()
        widget = self["config"]
        try:
            widget.list = entries
        except Exception:
            pass
        try:
            widget.l.setList(entries)
        except Exception:
            pass
        self.explain()

    def explain(self):
        try:
            index = self["config"].getCurrentIndex()
        except Exception:
            index = 0
        if 0 <= index < len(self.notes):
            self.say("note", self.notes[index])

    def store(self):
        for _, attr, _ in self.FIELDS:
            getattr(opts, attr).save()
        persist()
        self.close(True)

    def discard(self):
        for _, attr, _ in self.FIELDS:
            getattr(opts, attr).cancel()
        self.close(False)


class PrefsDeck(_Form):
    KEY = "settings"
    FIELDS = FIELDS
    BODY = """
        <widget name="config" position="48,120" size="1184,387" itemHeight="43" font="Regular;21" backgroundColor="{CARD}" {SEL:settings} foregroundColor="{TEXT}" foregroundColorSelected="{WHITE}" scrollbarMode="showOnDemand" />
        <widget name="note" position="72,556" size="1150,84" font="Regular;18" foregroundColor="{SOFT}" backgroundColor="{CARD}" transparent="1" valign="center" />"""

    def __init__(self, session, *rest):
        Page.__init__(self, session, "Ayarlar", "Sol / sağ ile değiştirin  ·  değişiklikler bir sonraki kurulumda uygulanır",
                      ("İptal", "Kaydet", "Varsayılanlar", ""))
        ConfigListScreen.__init__(self, self._mount(), session=session)
        self["note"] = Label("")
        self["remote"] = ActionMap(["ColorActions", "SetupActions"], {
            "ok": self.store, "save": self.store, "green": self.store,
            "cancel": self.discard, "red": self.discard, "yellow": self.defaults}, -2)
        try:
            self["config"].onSelectionChanged.append(self.explain)
        except Exception:
            pass
        self.onLayoutFinish.append(self.explain)

    def defaults(self):
        for _, attr, _ in self.FIELDS:
            element = getattr(opts, attr)
            try:
                element.value = element.default
            except Exception:
                pass
        self._remount()


class TimerDeck(_Form):
    KEY = "auto"
    FIELDS = AUTO_FIELDS
    BODY = """
        <widget name="config" position="48,120" size="1184,258" itemHeight="43" font="Regular;21" backgroundColor="{CARD}" {SEL:settings} foregroundColor="{TEXT}" foregroundColorSelected="{WHITE}" scrollbarMode="showOnDemand" />
        <widget name="note" position="56,384" size="1170,44" font="Regular;16" foregroundColor="{SOFT}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="cap0" position="60,466" size="340,22" font="Regular;14" foregroundColor="{CYAN}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="val0" position="60,494" size="340,48" font="Regular;28" foregroundColor="{WHITE}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="det0" position="60,548" size="340,90" font="Regular;15" foregroundColor="{MUTED}" backgroundColor="{CARD}" transparent="1" />
        <widget name="cap1" position="472,466" size="340,22" font="Regular;14" foregroundColor="{CYAN}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="val1" position="472,494" size="340,48" font="Regular;28" foregroundColor="{WHITE}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="det1" position="472,548" size="340,90" font="Regular;15" foregroundColor="{MUTED}" backgroundColor="{CARD}" transparent="1" />
        <widget name="cap2" position="884,466" size="340,22" font="Regular;14" foregroundColor="{CYAN}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="val2" position="884,494" size="340,48" font="Regular;28" foregroundColor="{WHITE}" backgroundColor="{CARD}" transparent="1" valign="center" />
        <widget name="det2" position="884,548" size="340,90" font="Regular;15" foregroundColor="{MUTED}" backgroundColor="{CARD}" transparent="1" />"""

    WATCHED = ("auto", "auto_time", "auto_day", "auto_date", "auto_standby")

    def __init__(self, session, *rest):
        Page.__init__(self, session, "Otomatik Güncelleme", "Arka planda TKGS kontrolü  ·  yalnızca değişiklik olduğunda kurulum",
                      ("İptal", "Kaydet", "Şimdi Dene", ""))
        ConfigListScreen.__init__(self, self._mount(), session=session)
        self.labels("note", "cap0", "cap1", "cap2", "val0", "val1", "val2", "det0", "det1", "det2")
        self["remote"] = ActionMap(["ColorActions", "SetupActions"], {
            "ok": self.store, "save": self.store, "green": self.store,
            "cancel": self.discard, "red": self.discard, "yellow": self.try_now}, -2)
        self.alive = True
        self.hooks = []
        for attr in self.WATCHED:
            element = getattr(opts, attr)
            try:
                element.addNotifier(self._changed, initial_call=False)
                self.hooks.append(element)
            except Exception:
                pass
        try:
            self["config"].onSelectionChanged.append(self.explain)
        except Exception:
            pass
        self.onLayoutFinish.append(self._first)
        self.onClose.append(self._unhook)

    def _entries(self):
        mode = opts.auto.value
        skip = set()
        if mode == "off":
            skip = {"auto_time", "auto_day", "auto_date", "auto_standby", "auto_changed", "auto_notify"}
        elif mode == "daily":
            skip = {"auto_day", "auto_date"}
        elif mode == "weekly":
            skip = {"auto_date"}
        else:
            skip = {"auto_day"}
        return [f for f in self.FIELDS if f[1] not in skip]

    def _first(self):
        self.explain()
        self.cards()

    def _changed(self, element=None):
        if not self.alive:
            return
        if element is opts.auto:
            self._remount()
        self.cards()

    def _unhook(self):
        self.alive = False
        for element in self.hooks:
            try:
                element.removeNotifier(self._changed)
            except Exception:
                pass

    def cards(self):
        mem = engine.Memory.read()
        on = opts.auto.value != "off"
        self.say("cap0", "DURUM")
        self.say("val0", auto.Planner.summary())
        paint(self["val0"], L.GREEN if on else L.MUTED)
        self.say("det0", ("Bekleme modunda çalışır, izlenen yayın kesilmez." if opts.auto_standby.value
                          else "Boş tuner varsa yayını bölmeden çalışır.") if on else "Önerilen: Her gün 04:00, bekleme modunda.")
        self.say("cap1", "SONRAKİ KONTROL")
        self.say("val1", auto.Planner.upcoming() if on else "-")
        self.say("det1", "Kutu o saatte kapalıysa açıldığında ilk fırsatta yapılır." if on else "")
        self.say("cap2", "SON SONUÇ")
        self.say("val2", engine.stamp(mem["auto_last"]) if mem.get("auto_last") else "-")
        paint(self["val2"], L.WHITE if mem.get("auto_ok", True) else L.AMBER)
        self.say("det2", native(mem.get("auto_note", "Henüz otomatik kontrol yapılmadı.")))

    def try_now(self):
        watcher = auto.Watcher.boot(self.session)
        if watcher.running or self.session.nav is None:
            return
        if not watcher.run_now(self._ran):
            return self.session.open(MessageBox, "Şu anda başka bir TKGS işlemi sürüyor.", MessageBox.TYPE_INFO, timeout=4)
        self.cards()

    def _ran(self):
        if self.alive:
            self.cards()


class LogDeck(Page):
    KEY = "report"
    BODY = """
        <widget name="text" position="60,122" size="1160,510" font="Regular;19" foregroundColor="{TEXT}" backgroundColor="{CARD}" />"""

    def __init__(self, session, *rest):
        Page.__init__(self, session, "Rapor ve Hakkında", "Yukarı / aşağı: sayfa  ·  sarı: rapor / tanı kaydı",
                      ("Kapat", "", "Tanı Kaydı", ""))
        self["text"] = ScrollLabel("")
        self.view = "report"
        self["remote"] = ActionMap(["DirectionActions", "ColorActions", "OkCancelActions"], {
            "cancel": self.close, "red": self.close, "ok": self.close,
            "yellow": self.flip, "blue": self.wipe_journal,
            "up": self["text"].pageUp, "down": self["text"].pageDown,
            "left": self["text"].pageUp, "right": self["text"].pageDown}, -1)
        self.onLayoutFinish.append(self.show_view)

    @staticmethod
    def _read(path, empty):
        if os.path.exists(path):
            try:
                return slurp(path) or empty
            except Exception:
                pass
        return empty

    def show_view(self):
        if self.view == "report":
            body = self._read(engine.REPORT, u"Henüz rapor yok. Bir TKGS okuması yapın veya Kanal Gezgini'ni açın.\n")
            body += (u"\n%s  ·  v%s\nby %s  ·  %s\nTürksat 42.0E TKGS tablosundan (PID 8181) taramasız kanal listesi kurulumu.\n"
                     u"İnternet veya harici sunucu kullanmaz.  Python 2/3  ·  ARM / MIPS  ·  ipk / deb\n"
                     % (uni(NAME), uni(VERSION), uni(AUTHOR), uni(HANDLE)))
            self.say("t_sub", "Son işlemin raporu  ·  " + engine.REPORT)
            self.buttons("Kapat", "", "Tanı Kaydı", "")
        else:
            path = Journal.path()
            hint = (u"Tanı kaydı kapalı. Ayarlar > Tanı kaydı seçeneğini açıp işlemi tekrarlayın.\n"
                    if not Journal.active() else u"Tanı kaydı açık, ancak henüz kayıt yok. Bir okuma yapın.\n")
            body = self._read(path, hint)
            if len(body) > 60000:
                body = u"... (yalnızca son kısım gösteriliyor)\n" + body[-60000:]
            self.say("t_sub", "Tanı kaydı  ·  " + path)
            self.buttons("Kapat", "", "Rapor", "Kaydı Temizle")
        self["text"].setText(native(body))
        if self.view != "report":
            try:
                self["text"].lastPage()
            except Exception:
                pass

    def flip(self):
        self.view = "journal" if self.view == "report" else "report"
        self.show_view()

    def wipe_journal(self):
        if self.view != "journal":
            return
        try:
            os.remove(Journal.path())
        except OSError:
            pass
        Journal.opened = False
        self.show_view()
