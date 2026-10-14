# -*- coding: utf-8 -*-
import os
import re

from enigma import (eListboxPythonMultiContent, getDesktop, gFont,
                    RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER)

from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText

try:
    from Components.MultiContent import MultiContentEntryPixmapAlphaBlend as _Picture
except ImportError:
    from Components.MultiContent import MultiContentEntryPixmapAlphaTest as _Picture

try:
    from enigma import gRGB
except ImportError:
    gRGB = None

try:
    from Tools.LoadPixmap import LoadPixmap
except ImportError:
    LoadPixmap = None

from . import layout as L
from .compat import native

LEFT = RT_HALIGN_LEFT | RT_VALIGN_CENTER
RIGHT = RT_HALIGN_RIGHT | RT_VALIGN_CENTER
CENTER = RT_HALIGN_CENTER | RT_VALIGN_CENTER
HOME = os.path.dirname(os.path.abspath(__file__))
PALETTE = dict((name, getattr(L, name)) for name in L.COLOR_NAMES)


class Theme(object):
    _ratio = None
    _cache = {}

    @classmethod
    def ratio(cls):
        if cls._ratio is None:
            try:
                span = getDesktop(0).size().width()
            except Exception:
                span = L.W
            cls._ratio = float(span) / L.W if span else 1.0
        return cls._ratio

    @classmethod
    def px(cls, value):
        return int(round(value * cls.ratio()))

    @classmethod
    def folder(cls):
        r = cls.ratio()
        tag = "hd" if abs(r - 1.0) < 0.01 else ("fhd" if abs(r - 1.5) < 0.01 else None)
        path = tag and os.path.join(HOME, "images", tag)
        return path if path and os.path.isdir(path) else None

    @classmethod
    def image(cls, name):
        root = cls.folder()
        path = root and os.path.join(root, name + ".png")
        return path if path and os.path.exists(path) else None

    @classmethod
    def pixmap(cls, name):
        if LoadPixmap is None:
            return None
        if name not in cls._cache:
            path = cls.image(name)
            try:
                cls._cache[name] = LoadPixmap(cached=True, path=path) if path else None
            except TypeError:
                cls._cache[name] = LoadPixmap(path) if path else None
            except Exception:
                cls._cache[name] = None
        return cls._cache[name]

    @staticmethod
    def hexa(value):
        return "#00%06x" % value

    @classmethod
    def _backdrop(cls, key):
        art = cls.image("bg_" + key)
        if art:
            return '<ePixmap pixmap="%s" position="0,0" size="%d,%d" zPosition="-10" />' % (art, L.W, L.H)
        parts = []
        for kind, x, y, w, h, color, _ in L.FRAME + L.PANELS.get(key, ()):
            parts.append('<eLabel position="%d,%d" size="%d,%d" backgroundColor="%s" zPosition="-9" />'
                         % (x, y, w, h, cls.hexa(L.EDGE if kind == "card" else color)))
            if kind == "card":
                parts.append('<eLabel position="%d,%d" size="%d,%d" backgroundColor="%s" zPosition="-9" />'
                             % (x + 1, y + 1, w - 2, h - 2, cls.hexa(color)))
        for x, color in L.KEYS:
            parts.append('<eLabel position="%d,688" size="12,12" backgroundColor="%s" zPosition="-9" />'
                         % (x, cls.hexa(color)))
        return "".join(parts)

    @classmethod
    def _brand(cls):
        logo = cls.image("logo")
        mark = ('<ePixmap pixmap="%s" position="32,20" size="48,48" alphatest="blend" zPosition="1" />' % logo
                if logo else '<eLabel position="32,20" size="48,48" backgroundColor="{CYAN}" />')
        return mark + """
        <eLabel text="TKGS" position="94,12" size="200,38" font="Regular;32" foregroundColor="{WHITE}" backgroundColor="{DUSK}" transparent="1" valign="center" />
        <eLabel text="by Murat SEVER" position="95,50" size="200,22" font="Regular;15" foregroundColor="{CYAN}" backgroundColor="{DUSK}" transparent="1" valign="center" />
        <widget name="t_title" position="324,12" size="620,38" font="Regular;27" foregroundColor="{TEXT}" backgroundColor="{DUSK}" transparent="1" valign="center" />
        <widget name="t_sub" position="324,50" size="680,24" font="Regular;16" foregroundColor="{MUTED}" backgroundColor="{DUSK}" transparent="1" valign="center" />
        <widget source="global.CurrentTime" render="Label" position="1040,8" size="200,46" font="Regular;38" halign="right" valign="center" foregroundColor="{TEXT}" backgroundColor="{DUSK}" transparent="1">
            <convert type="ClockToText">Default</convert>
        </widget>
        <widget source="global.CurrentTime" render="Label" position="980,52" size="260,24" font="Regular;16" halign="right" valign="center" foregroundColor="{MUTED}" backgroundColor="{DUSK}" transparent="1">
            <convert type="ClockToText">Format:%d.%m.%Y</convert>
        </widget>"""

    @classmethod
    def _keys(cls):
        return "".join(
            '<widget name="k_%s" position="%d,676" size="250,36" font="Regular;19" foregroundColor="{TEXT}" '
            'backgroundColor="{DUSK}" transparent="1" valign="center" />' % (name, x + 22)
            for name, (x, _) in zip(("red", "green", "yellow", "blue"), L.KEYS))

    @classmethod
    def compose(cls, key, body):
        xml = ('<screen name="MSTKGS_%s" position="0,0" size="%d,%d" flags="wfNoBorder" backgroundColor="{INK}" title="TKGS">'
               % (key, L.W, L.H) + cls._backdrop(key) + cls._brand() + body + cls._keys() + "</screen>")
        for name, value in PALETTE.items():
            xml = xml.replace("{%s}" % name, cls.hexa(value))
        xml = re.sub(r"\{SEL:(\w+)\}", lambda m: cls._selection(m.group(1)), xml)
        return cls.scale(xml)

    @classmethod
    def _selection(cls, name):
        path = cls.image("sel_" + name)
        return ('selectionPixmap="%s" backgroundColorSelected="%s"' % (path, cls.hexa(L.CARD)) if path
                else 'backgroundColorSelected="%s"' % cls.hexa(L.LIFT))

    @classmethod
    def scale(cls, xml):
        r = cls.ratio()
        if abs(r - 1.0) < 0.01:
            return xml

        def numbers(m):
            values = [str(int(round(int(v) * r))) if v.strip().isdigit() else v for v in m.group(2).split(",")]
            return '%s="%s"' % (m.group(1), ",".join(values))

        xml = re.sub(r'\b(position|size|itemHeight|borderWidth)="([^"]+)"', numbers, xml)
        return re.sub(r'font="([A-Za-z]+);(\d+)"',
                      lambda m: 'font="%s;%d"' % (m.group(1), max(10, int(round(int(m.group(2)) * r)))), xml)

    @classmethod
    def art(cls, name, image, x, y, w, h, color, z=1):
        path = cls.image(image)
        if path:
            return ('<widget name="%s" pixmap="%s" position="%d,%d" size="%d,%d" alphatest="blend" zPosition="%d" />'
                    % (name, path, x, y, w, h, z))
        return ('<widget name="%s" position="%d,%d" size="%d,%d" font="Regular;10" backgroundColor="%s" zPosition="%d" />'
                % (name, x, y, w, h, cls.hexa(color), z))

    @classmethod
    def rich(cls):
        return cls.folder() is not None


def swap(widget, image, color):
    art = Theme.pixmap(image) if Theme.image(image) else None
    if art is not None:
        try:
            widget.instance.setPixmap(art)
            return
        except Exception:
            pass
    paint(widget, back=color)


def paint(widget, fore=None, back=None):
    if gRGB is None or widget.instance is None:
        return
    try:
        if back is not None:
            widget.instance.setBackgroundColor(gRGB(back))
        if fore is not None:
            widget.instance.setForegroundColor(gRGB(fore))
    except Exception:
        pass


def step(widget, how):
    try:
        widget.instance.moveSelection(getattr(widget.instance, how))
    except Exception:
        pass


def listbox(fonts, row):
    try:
        box = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
    except TypeError:
        box = MenuList([], True, eListboxPythonMultiContent)
    shape_list(box, fonts, row)
    return box


def shape_list(box, fonts, row):
    try:
        for slot, size in enumerate(fonts):
            box.l.setFont(slot, gFont("Regular", Theme.px(size)))
        box.l.setItemHeight(Theme.px(row))
    except Exception:
        pass


def cell(x, y, w, h, value, font=0, fore=L.TEXT, chosen=L.WHITE, align=LEFT, back=None, back_chosen=None):
    px = Theme.px
    extra = {}
    if back is not None:
        extra["backcolor"] = back
        extra["backcolor_sel"] = back if back_chosen is None else back_chosen
    return MultiContentEntryText(pos=(px(x), px(y)), size=(px(w), px(h)), font=font, flags=align,
                                 text=native(value), color=fore, color_sel=chosen, **extra)


def picture(x, y, w, h, name):
    art = Theme.pixmap(name)
    if art is None:
        return None
    px = Theme.px
    return _Picture(pos=(px(x), px(y)), size=(px(w), px(h)), png=art)
