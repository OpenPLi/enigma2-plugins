# -*- coding: utf-8 -*-
# for localized messages
from . import _

from Plugins.Plugin import PluginDescriptor
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigText

##################################
pname = _("Filebrowser")
pdesc = _("manage local Files")

config.plugins.filebrowser = ConfigSubsection()
config.plugins.filebrowser.add_mainmenu_entry = ConfigYesNo(default=False)
config.plugins.filebrowser.add_extensionmenu_entry = ConfigYesNo(default=False)
config.plugins.filebrowser.savedirs = ConfigYesNo(default=True)
config.plugins.filebrowser.path_left = ConfigText(default="/")
config.plugins.filebrowser.path_right = ConfigText(default="/")
config.plugins.filebrowser.dir_size = ConfigYesNo(default=False)

##################################

def filescan_open(list, session, **kwargs):
    path = "/".join(list[0].path.split("/")[:-1]) + "/"
    import ui
    session.open(ui.FilebrowserScreen,path_left=path)

def start_from_filescan(**kwargs):
    from Components.Scanner import Scanner, ScanPath
    return \
        Scanner(mimetypes=None,
            paths_to_scan=[
                    ScanPath(path="", with_subdirs=False),
                ],
            name=pname,
            description=pdesc,
            openfnc=filescan_open,
        )

def start_from_mainmenu(menuid, **kwargs):
    #starting from main menu
    if menuid == "mainmenu":
        return [(pname, start_from_pluginmenu, "filecommand", 46)]
    return []

def start_from_pluginmenu(session,**kwargs):
    import ui
    session.open(ui.FilebrowserScreen)

def Plugins(path,**kwargs):
    desc_mainmenu = PluginDescriptor(name=pname, description=pdesc, where=PluginDescriptor.WHERE_MENU, fnc=start_from_mainmenu)
    desc_pluginmenu = PluginDescriptor(name=pname, description=pdesc, where=PluginDescriptor.WHERE_PLUGINMENU, fnc=start_from_pluginmenu)
    desc_extensionmenu = PluginDescriptor(name=pname, description=pdesc, where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=start_from_pluginmenu)
    desc_filescan = PluginDescriptor(name=pname, where=PluginDescriptor.WHERE_FILESCAN, fnc=start_from_filescan)
    list = []
    list.append(desc_pluginmenu)
    #buggie list.append(desc_filescan)
    if config.plugins.filebrowser.add_extensionmenu_entry.value:
        list.append(desc_extensionmenu)
    if config.plugins.filebrowser.add_mainmenu_entry.value:
        list.append(desc_mainmenu)
    return list
