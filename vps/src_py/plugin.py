# -*- coding: utf-8 -*-

from Plugins.Plugin import PluginDescriptor
from os import stat
from Vps import vps_timers
from Vps_setup import VPS_Setup
from Modifications import register_vps
from . import _

# Config
from Components.config import config, ConfigYesNo, ConfigSubsection, ConfigInteger, ConfigSelection, configfile

config.plugins.vps = ConfigSubsection()
config.plugins.vps.enabled = ConfigYesNo(default=True)
config.plugins.vps.do_PDC_check = ConfigYesNo(default=True)
config.plugins.vps.initial_time = ConfigInteger(default=10, limits=(0, 120))
config.plugins.vps.allow_wakeup = ConfigYesNo(default=False)
config.plugins.vps.allow_seeking_multiple_pdc = ConfigYesNo(default=True)
config.plugins.vps.vps_default = ConfigSelection(choices=[("no", _("No")), ("yes_safe", _("Yes (safe mode)")), ("yes", _("Yes"))], default="no")
config.plugins.vps.instanttimer = ConfigSelection(choices=[("no", _("No")), ("yes_safe", _("Yes (safe mode)")), ("yes", _("Yes")), ("ask", _("always ask"))], default="ask")
config.plugins.vps.infotext = ConfigInteger(default=0)
config.plugins.vps.margin_after = ConfigInteger(default=10, limits=(0, 600)) # in seconds
config.plugins.vps.wakeup_time = ConfigInteger(default=-1)


recordTimerWakeupAuto = False


def autostart(reason, **kwargs):
	if reason == 0:
		if "session" in kwargs:
			session = kwargs["session"]
			vps_timers.session = session
			vps_timers.checkTimer()
		else:
			register_vps()

	elif reason == 1:
		vps_timers.shutdown()

		try:
			if config.plugins.vps.wakeup_time.value != -1 and config.plugins.vps.wakeup_time.value == config.misc.prev_wakeup_time.value:
				config.misc.prev_wakeup_time_type.value = 0
				config.misc.prev_wakeup_time_type.save()
				configfile.save()
		except:
			print "[VPS-Plugin] exception in shutdown handler, probably old enigma2"


def setup(session, **kwargs):
	session.openWithCallback(doneConfig, VPS_Setup)


def doneConfig(session, **kwargs):
	vps_timers.checkTimer()


def startSetup(menuid):
	if menuid != "system":
		return []
	return [(_("VPS Settings"), setup, "vps", 50)]


def getNextWakeup():
	global recordTimerWakeupAuto
	t, recordTimerWakeupAuto = vps_timers.nextWakeup()
	config.plugins.vps.wakeup_time.value = t
	config.plugins.vps.save()

	return t


def Plugins(**kwargs):
	return [
		PluginDescriptor(
			name="VPS",
			where=[
				PluginDescriptor.WHERE_AUTOSTART,
				PluginDescriptor.WHERE_SESSIONSTART
			],
			fnc=autostart,
			wakeupfnc=getNextWakeup,
			needsRestart=True
		),
		PluginDescriptor(
			name=_("VPS Settings"),
			where=PluginDescriptor.WHERE_MENU,
			fnc=startSetup,
			needsRestart=True
		),
	]
