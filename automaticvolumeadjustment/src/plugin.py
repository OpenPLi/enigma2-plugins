# -*- coding: utf-8 -*-
#
#  AutomaticVolumeAdjustment E2
#
#  $Id$
#
#  Coded by Dr.Best (c) 2010
#  Support: www.dreambox-tools.info
#
#  This plugin is licensed under the Creative Commons
#  Attribution-NonCommercial-ShareAlike 3.0 Unported
#  License. To view a copy of this license, visit
#  http://creativecommons.org/licenses/by-nc-sa/3.0/ or send a letter to Creative
#  Commons, 559 Nathan Abbott Way, Stanford, California 94305, USA.
#
#  Alternatively, this plugin may be distributed and executed on hardware which
#  is licensed by Dream Multimedia GmbH.

#  This plugin is NOT free software. It is open source, you are allowed to
#  modify it (if you keep the license), but it may not be commercially
#  distributed other than under the conditions noted above.
#
# for localized messages
from . import _
from Plugins.Plugin import PluginDescriptor
from Components.config import config, ConfigYesNo, NoSave
from Screens.MessageBox import MessageBox
from AutomaticVolumeAdjustmentSetup import AutomaticVolumeAdjustmentConfigScreen
from AutomaticVolumeAdjustment import AutomaticVolumeAdjustment
from AutomaticVolumeAdjustmentConfig import saveVolumeDict

config.misc.AV_audio_menu = ConfigYesNo(default=False)
config.misc.toggle_AV_session = NoSave(ConfigYesNo(default=True))


def audioMenu(session, **kwargs):
	status = config.misc.toggle_AV_session.value and _("Disable") or _("Enable")
	session.openWithCallback(toggleAVclosed, MessageBox, _("%s plugin only this session?") % status, MessageBox.TYPE_YESNO)


def toggleAVclosed(ret):
	if ret:
		config.misc.toggle_AV_session.value = not config.misc.toggle_AV_session.value



def autostart(reason, **kwargs):
	if "session" in kwargs:
		session = kwargs["session"]
		AutomaticVolumeAdjustment(session)


def autoend(reason, **kwargs):
	# save config values for last used volume modus
	if reason == 1:
		if AutomaticVolumeAdjustment.instance:
			if AutomaticVolumeAdjustment.instance.enabled and AutomaticVolumeAdjustment.instance.modus != "0":
				saveVolumeDict(AutomaticVolumeAdjustment.instance.serviceList)


def setupAVA(session, **kwargs):
	session.open(AutomaticVolumeAdjustmentConfigScreen) # start setup


def startSetup(menuid):
	if menuid != "video": # show setup only in system level menu
		return []
	return [(_("Automatic Volume Adjustment"), setupAVA, "AutomaticVolumeAdjustment", 0)]


def Plugins(**kwargs):
	l = [PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=autostart), PluginDescriptor(where=[PluginDescriptor.WHERE_AUTOSTART], fnc=autoend),
		PluginDescriptor(name="Automatic Volume Adjustment", description=_("Automatic Volume Adjustment"), where=PluginDescriptor.WHERE_MENU, fnc=startSetup)]
	if config.misc.AV_audio_menu.value:
		l.append((PluginDescriptor(name=_("Automatic Volume Adjustment"), description=_("toggle on/off plugin only for session"), where=PluginDescriptor.WHERE_AUDIOMENU, fnc=audioMenu)))
	return l
