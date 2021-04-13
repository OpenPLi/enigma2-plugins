# -*- coding: UTF-8 -*-
## Zap-History Browser by AliAbdul
from . import _
from Plugins.Plugin import PluginDescriptor


def main(session, servicelist, **kwargs):
	import ui
	session.open(ui.ZapHistoryBrowser, servicelist)


def Plugins(**kwargs):
	return PluginDescriptor(name=_("Zap-History Browser"), where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main)
