from . import _

from Plugins.Plugin import PluginDescriptor
from Components.config import config
from Components.ActionMap import ActionMap
from PrimeTimeManager import PrimeTimeManager
from PrimeTimeSettings import PrimeTimeSettings

baseTimerEditList__init__ = None

def eventinfo(session,  servicelist, **kwargs):
	session.open(PrimeTimeManager, servicelist)

def main(session, **kwargs):
	servicelist = kwargs.get('servicelist', None)
	session.open(PrimeTimeManager, servicelist)

def settings(session, **kwargs):
	session.open(PrimeTimeSettings)

def autostart(reason, **kwargs):
	global baseTimerEditList__init__
	if reason == 0 and baseTimerEditList__init__ is None:
		try:
			from Screens.TimerEdit import TimerEditList
			baseTimerEditList__init__ = TimerEditList.__init__
			from PrimeTimeTimerEdit import PMTimerEditList__init__, openExtendedSetup, updateList
			TimerEditList.__init__ = PMTimerEditList__init__
			TimerEditList.openExtendedSetup = openExtendedSetup
			TimerEditList.updateList = updateList
		except:
			pass

def Plugins(**kwargs):
	list = [PluginDescriptor(name = _("Prime Time Manager setup"), description = _("Settings of the plugin"), where = PluginDescriptor.WHERE_PLUGINMENU, icon = "plugin.png", fnc = settings)]
	list.append(PluginDescriptor(name = _("Prime Time Manager"), description = _("Manage prime time events"), where = PluginDescriptor.WHERE_EVENTINFO, fnc = eventinfo))
	list.append(PluginDescriptor(name = "Timer Edit key menu - show conflict timer", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = autostart))
	if config.plugins.PrimeTimeManager.ExtMenu.value:
		list.append(PluginDescriptor(name = _("Prime Time Manager "), description = _("Manage prime time events"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc = main))
	return list
