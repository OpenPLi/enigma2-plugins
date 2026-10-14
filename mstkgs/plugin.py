# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor

from .conf import MENU_NAME, NAME, opts


def launch(session, **extra):
    from .ui import ControlDeck
    session.open(ControlDeck)


def menu_entry(menu_id, **extra):
    spots = {"scan": ("mstkgs", None)}
    if opts.mainmenu.value:
        spots["mainmenu"] = ("mstkgs_main", 45)
    spot = spots.get(menu_id)
    return [(MENU_NAME, launch, spot[0], spot[1])] if spot else []


def startup(reason, session=None, **extra):
    if reason == 0 and session is not None:
        try:
            from .auto import Watcher
            Watcher.boot(session)
        except Exception:
            pass


def Plugins(**extra):
    about = "Türksat TKGS: taramasız kanal listesi, otomatik güncelleme, kanal gezgini"
    places = (PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU)
    found = [PluginDescriptor(name=NAME, description=about, where=where, fnc=launch,
                              **({"icon": "plugin.png"} if where == PluginDescriptor.WHERE_PLUGINMENU else {}))
             for where in places]
    found.append(PluginDescriptor(name=NAME, description=about, where=PluginDescriptor.WHERE_MENU, fnc=menu_entry))
    found.append(PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=startup))
    return found
