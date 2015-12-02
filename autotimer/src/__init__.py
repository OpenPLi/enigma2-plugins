# -*- coding: utf-8 -*-
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from os import environ as os_environ
import gettext

# Config
from Components.config import config, ConfigSubsection, ConfigEnableDisable, \
	ConfigNumber, ConfigSelection, ConfigYesNo
	
def localeInit():
	gettext.bindtextdomain("AutoTimer", resolveFilename(SCOPE_PLUGINS, "Extensions/AutoTimer/locale"))

def _(txt):
	t = gettext.dgettext("AutoTimer", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)


config.plugins.autotimer = ConfigSubsection()
config.plugins.autotimer.autopoll = ConfigEnableDisable(default=True)
config.plugins.autotimer.delay = ConfigNumber(default=3)
config.plugins.autotimer.editdelay = ConfigNumber(default=3)
config.plugins.autotimer.interval = ConfigNumber(default=12)
config.plugins.autotimer.timeout = ConfigNumber(default=5)
config.plugins.autotimer.popup_timeout = ConfigNumber(default=5)
config.plugins.autotimer.check_eit_and_remove = ConfigEnableDisable(default=False)
config.plugins.autotimer.refresh = ConfigSelection(choices=[
		("none", _("None")),
		("auto", _("Only AutoTimers created during this session")),
		("all", _("All non-repeating timers"))
	], default="none"
)
if config.plugins.autotimer.interval.value == 0:
	config.plugins.autotimer.interval.value = 1
	config.plugins.autotimer.interval.save()
if config.plugins.autotimer.timeout.value == 0:
	config.plugins.autotimer.timeout.value = 1
	config.plugins.autotimer.timeout.save()
config.plugins.autotimer.add_to_channelselection = ConfigYesNo(default=False)
config.plugins.autotimer.add_to_epgselection = ConfigYesNo(default=False)
config.plugins.autotimer.add_to_multiepgselection = ConfigYesNo(default=False)
config.plugins.autotimer.add_to_graph = ConfigYesNo(default=False) 
config.plugins.autotimer.try_guessing = ConfigEnableDisable(default=True)
config.plugins.autotimer.editor = ConfigSelection(choices=[
		("plain", _("Classic")),
		("wizard", _("Wizard"))
	], default="wizard"
)
config.plugins.autotimer.addsimilar_on_conflict = ConfigEnableDisable(default=False)
config.plugins.autotimer.onlyinstandby = ConfigYesNo(default=False)
config.plugins.autotimer.add_autotimer_to_tags = ConfigYesNo(default=False)
config.plugins.autotimer.add_name_to_tags = ConfigYesNo(default=False)
config.plugins.autotimer.disabled_on_conflict = ConfigEnableDisable(default=False)
config.plugins.autotimer.show_in_extensionsmenu = ConfigYesNo(default=False)
config.plugins.autotimer.show_in_furtheroptionsmenu = ConfigYesNo(default = True)
config.plugins.autotimer.fastscan = ConfigYesNo(default=False)
config.plugins.autotimer.notifconflict = ConfigYesNo(default=True)
config.plugins.autotimer.notifsimilar = ConfigYesNo(default=True)
config.plugins.autotimer.notiftimers = ConfigYesNo(default=False)
config.plugins.autotimer.maxdaysinfuture = ConfigNumber(default=0)
config.plugins.autotimer.show_help = ConfigYesNo(default=True)
config.plugins.autotimer.skip_during_records = ConfigYesNo(default=False)
config.plugins.autotimer.skip_during_epgrefresh = ConfigYesNo(default=False)
config.plugins.autotimer.style_autotimerslist = ConfigSelection(choices=[
		("standard", _("Standard")),
		("advanced", _("Advanced"))
	], default="standard"
)

try:
	xrange = xrange
	iteritems = lambda d: d.iteritems()
	itervalues = lambda d: d.itervalues()
except NameError:
	xrange = range
	iteritems = lambda d: d.items()
	itervalues = lambda d: d.values()

__all__ = ['_', 'config', 'iteritems', 'itervalues', 'xrange']
