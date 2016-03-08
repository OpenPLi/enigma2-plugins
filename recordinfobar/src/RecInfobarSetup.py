from . import _, PLUGIN_NAME
from Screens.Screen import Screen
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
import plugin

plugin_version = "1.22"

class RecInfobarSetupScreen(Screen, ConfigListScreen):
	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		self.skinName = ["RecInfobarSetup", "Setup"]
		self.setup_title = _("Record Infobar Setup")

		self["key_green"] = StaticText(_("OK"))
		self["key_red"] = StaticText(_("Cancel"))
		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"cancel": self.keyRed,
			"ok": self.keyOk,
			"save": self.keyGreen,
		}, -1)
		ConfigListScreen.__init__(self, [])
		self.initConfig()
		self.createSetup()
		self.onClose.append(self.__closed)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __closed(self):
		pass

	def __layoutFinished(self):
		self.setTitle(self.setup_title + ": " + plugin_version)

	def initConfig(self):
		self.RIB = config.plugins.RecInfobar
		self.prev_enable = config.usage.recinfobar.value
		self.prev_anchor = self.RIB.anchor.value
		self.prev_X = self.RIB.x.value
		self.prev_Y = self.RIB.y.value
		self.prev_always_zap = self.RIB.always_zap.value
		self.prev_always_message = self.RIB.always_message.value
		self.prev_default_zap = self.RIB.default_zap.value
		self.prev_check_wakeup = self.RIB.check_wakeup.value
		self.prev_standby_timeout = self.RIB.standby_timeout.value
		self.prev_after_event = self.RIB.after_event.value
		self.prev_set_position = self.RIB.set_position.value
		self.prev_Z = self.RIB.z.value
		self.prev_background = self.RIB.background.value
		self.prev_format = self.RIB.timelen_format.value
		self.prev_indicator_x = self.RIB.indicator_x.value
		self.prev_indicator_y = self.RIB.indicator_y.value
		self.prev_rec_indicator = self.RIB.rec_indicator.value
		self.prev_tuner_recording_priority = self.RIB.tuner_recording_priority.value
		self.cfg_enable = getConfigListEntry(_("Enable record infobar"), config.usage.recinfobar)
		self.cfg_anchor = getConfigListEntry(_("Anchor resizing at"), self.RIB.anchor)
		self.cfg_indicator_x = getConfigListEntry(_("X screen position"), self.RIB.indicator_x)
		self.cfg_indicator_y = getConfigListEntry(_("Y screen position"), self.RIB.indicator_y)
		self.cfg_rec_indicator = getConfigListEntry(_("Always show indicator icon when recording"), self.RIB.rec_indicator)
		self.cfg_x = getConfigListEntry(_("X screen position"), self.RIB.x)
		self.cfg_y = getConfigListEntry(_("Y screen position"), self.RIB.y)
		self.cfg_background = getConfigListEntry(_("Background window"), self.RIB.background)
		self.cfg_always_zap = getConfigListEntry(_("Zap on start service recording"), self.RIB.always_zap)
		self.cfg_always_message = getConfigListEntry(_("Show message when zap to recording service"), self.RIB.always_message)
		self.cfg_default_zap = getConfigListEntry(_("Automatic is the default action"), self.RIB.default_zap)
		self.cfg_check_wakeup = getConfigListEntry(_("Goto standby when wakeup on a timer recording"), self.RIB.check_wakeup)
		self.cfg_standby_timeout = getConfigListEntry(_("Standby message screen timeout (sec)"), self.RIB.standby_timeout)
		self.cfg_after_event = getConfigListEntry(_("Standby only type timer 'After event'"), self.RIB.after_event)
		self.cfg_set_position = getConfigListEntry(_("Set correct position timer in channel list"), self.RIB.set_position)
		self.cfg_help = getConfigListEntry(_("<<Only when zap to service at start timer>>"), self.RIB.help)
		self.cfg_z = getConfigListEntry(_("Z screen position"), self.RIB.z)
		self.cfg_format = getConfigListEntry(_("Record timelen format"), self.RIB.timelen_format)
		self.cfg_tuner_recording_priority = getConfigListEntry(_("Preferred tuner for recording"), self.RIB.tuner_recording_priority)

	def createSetup(self):
		list = [ self.cfg_enable ]
		if config.usage.recinfobar.value:
			list.append(self.cfg_anchor)
			list.append(self.cfg_x)
			list.append(self.cfg_y)
			list.append(self.cfg_z)
			list.append(self.cfg_background)
			list.append(self.cfg_format)
			list.append(self.cfg_always_zap)
			if config.plugins.RecInfobar.always_zap.value == "1":
				list.append(self.cfg_always_message)
			if config.plugins.RecInfobar.always_zap.value == "2":
				list.append(self.cfg_default_zap)
			list.append(self.cfg_check_wakeup)
			if config.plugins.RecInfobar.check_wakeup.value:
				list.append(self.cfg_after_event)
				list.append(self.cfg_standby_timeout)
			list.append(self.cfg_set_position)
			if config.plugins.RecInfobar.set_position.value:
				list.append(self.cfg_help)
			if not plugin.SUPPORT_PRIORITY:
				list.append(self.cfg_tuner_recording_priority)
			list.append(self.cfg_rec_indicator)
			if config.plugins.RecInfobar.rec_indicator.value:
				list.append(self.cfg_indicator_x)
				list.append(self.cfg_indicator_y)
		self["config"].list = list
		self["config"].l.setList(list)

	def newConfig(self):
		cur = self["config"].getCurrent()
		if cur in (self.cfg_enable, self.cfg_always_zap, self.cfg_check_wakeup, self.cfg_set_position, self.cfg_rec_indicator):
			self.createSetup()

	def keyOk(self):
		self.keyGreen()

	def keyRed(self):
		config.usage.recinfobar.value = self.prev_enable
		self.RIB.anchor.value = self.prev_anchor
		self.RIB.x.value = self.prev_X
		self.RIB.y.value = self.prev_Y
		self.RIB.always_zap.value = self.prev_always_zap
		self.RIB.always_message.value = self.prev_always_message
		self.RIB.default_zap.value = self.prev_default_zap
		self.RIB.check_wakeup.value = self.prev_check_wakeup
		self.RIB.standby_timeout.value = self.prev_standby_timeout
		self.RIB.after_event.value = self.prev_after_event
		self.RIB.set_position.value = self.prev_set_position
		self.RIB.z.value = self.prev_Z
		self.RIB.background.value = self.prev_background
		self.RIB.timelen_format.value = self.prev_format
		self.RIB.rec_indicator.value = self.prev_rec_indicator
		self.RIB.indicator_x.value = self.prev_indicator_x
		self.RIB.indicator_y.value = self.prev_indicator_y
		self.RIB.tuner_recording_priority.value = self.prev_tuner_recording_priority
		self.keyGreen()

	def keyGreen(self):
		if not config.usage.recinfobar.value:
			self.RIB.always_zap.value = "0"
			self.RIB.check_wakeup.value = False
			self.RIB.set_position.value = False
			self.RIB.rec_indicator.value = False
			self.RIB.tuner_recording_priority.value = "-2"
		if config.plugins.RecInfobar.always_zap.value != "1" and config.plugins.RecInfobar.always_message.value is True: 
			self.RIB.always_message.value = False
		if not config.plugins.RecInfobar.check_wakeup.value: 
			self.RIB.after_event.value = "5"
			self.RIB.standby_timeout.value = 10
		if config.plugins.RecInfobar.always_zap.value == "2" and not config.recording.asktozap.value:
			config.recording.asktozap.value = True
			config.recording.asktozap.save()
		if config.plugins.RecInfobar.always_zap.value == "2":
			config.misc.rectimerstate.value = False
			config.misc.rectimerstate.save()
		if config.plugins.RecInfobar.always_zap.value != "2":
			self.RIB.default_zap.value = "yes"
		if plugin.SUPPORT_PRIORITY and self.RIB.tuner_recording_priority.value != "-2":
			self.RIB.tuner_recording_priority.value = "-2"
		config.usage.recinfobar.save()
		self.RIB.anchor.save()
		self.RIB.x.save()
		self.RIB.y.save()
		self.RIB.always_zap.save()
		self.RIB.always_message.save()
		self.RIB.default_zap.save()
		self.RIB.check_wakeup.save()
		self.RIB.standby_timeout.save()
		self.RIB.after_event.save()
		self.RIB.set_position.save()
		self.RIB.z.save()
		self.RIB.background.save()
		self.RIB.timelen_format.save()
		self.RIB.rec_indicator.save()
		self.RIB.indicator_x.save()
		self.RIB.indicator_y.save()
		self.RIB.tuner_recording_priority.save()
		if self.prev_enable != config.usage.recinfobar.value or self.prev_Z != self.RIB.z.value or self.prev_background != self.RIB.background.value:
			self.session.openWithCallback(self.restartGuiNow, MessageBox, _("GUI needs a restart to apply changes.\nRestart the GUI now?"), MessageBox.TYPE_YESNO)
		else:
			self.close()

	def restartGuiNow(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()
