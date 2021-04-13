# -*- coding: utf-8 -*-

from . import _
from RecordTimer import RecordTimerEntry, RecordTimer
from Screens.TimerEntry import TimerEntry
from Components.config import config, ConfigSelection, ConfigText, ConfigSubList, ConfigDateTime, ConfigClock, ConfigYesNo, getConfigListEntry
from Tools import Directories
from Tools.XMLTools import stringToXML
from Tools import Notifications
from Screens.MessageBox import MessageBox
from Screens.InfoBarGenerics import InfoBarInstantRecord
from time import time
from enigma import getBestPlayableServiceReference, eServiceReference
import xml.etree.cElementTree
from Vps_setup import VPS_show_info

vps_already_registered = False


def new_RecordTimer_saveTimer(self):
	self._saveTimer_old_rn_vps()

	# added by VPS-Plugin
	list = []
	list.append('<?xml version="1.0" ?>\n')
	list.append('<vps_timers>\n')

	try:
		for timer in self.timer_list:
			if timer.dontSave or timer.vpsplugin_enabled is None or timer.vpsplugin_enabled == False:
				continue

			list.append('<timer')
			list.append(' begin="' + str(int(timer.begin)) + '"')
			list.append(' end="' + str(int(timer.end)) + '"')
			list.append(' serviceref="' + stringToXML(str(timer.service_ref)) + '"')
			list.append(' vps_enabled="1"')

			if timer.vpsplugin_overwrite is not None:
				list.append(' vps_overwrite="' + str(int(timer.vpsplugin_overwrite)) + '"')
			else:
				list.append(' vps_overwrite="0"')

			if timer.vpsplugin_time is not None:
				list.append(' vps_time="' + str(timer.vpsplugin_time) + '"')
			else:
				list.append(' vps_time="0"')

			list.append('>\n')
			list.append('</timer>\n')

		list.append('</vps_timers>\n')

		file = open(Directories.resolveFilename(Directories.SCOPE_CONFIG, "timers_vps.xml"), "w")
		for x in list:
			file.write(x)
		file.close()
	except:
	 pass
	# added by VPS-Plugin


def new_RecordTimer_loadTimer(self):
	# added by VPS-Plugin
	xmlroot = None
	try:
		global xml
		doc = xml.etree.cElementTree.parse(Directories.resolveFilename(Directories.SCOPE_CONFIG, "timers_vps.xml"))
		xmlroot = doc.getroot()
	except:
		pass
	# added by VPS-Plugin

	self._loadTimer_old_rn_vps()

	# added by VPS-Plugin
	try:
		vps_timers = {}

		if xmlroot is not None:
			for xml in xmlroot.findall("timer"):
				begin = xml.get("begin")
				end = xml.get("end")
				serviceref = xml.get("serviceref").encode("utf-8")

				vps_timers[serviceref + begin + end] = {}
				vps_overwrite = xml.get("vps_overwrite")
				if vps_overwrite and vps_overwrite == "1":
					vps_timers[serviceref + begin + end]["overwrite"] = True
				else:
					vps_timers[serviceref + begin + end]["overwrite"] = False

				vps_time = xml.get("vps_time")
				if vps_time and vps_time != "None":
					vps_timers[serviceref + begin + end]["time"] = int(vps_time)
				else:
					vps_timers[serviceref + begin + end]["time"] = 0

			for timer in self.timer_list:
				begin = str(timer.begin)
				end = str(timer.end)
				serviceref = str(timer.service_ref)

				if vps_timers.get(serviceref + begin + end, None) is not None:
					timer.vpsplugin_enabled = True
					timer.vpsplugin_overwrite = vps_timers[serviceref + begin + end]["overwrite"]
					if vps_timers[serviceref + begin + end]["time"] != 0:
						timer.vpsplugin_time = vps_timers[serviceref + begin + end]["time"]
				else:
					timer.vpsplugin_enabled = False
					timer.vpsplugin_overwrite = False
	except:
		pass
	# added by VPS-Plugin


def new_TimerEntry_createConfig(self):
	#self._createConfig_old_rn_vps()

	# added by VPS-Plugin
	try:
		self.timerentry_vpsplugin_dontcheck_pdc = not config.plugins.vps.do_PDC_check.getValue()
		default_value = "no"

		if self.timer.vpsplugin_enabled is not None:
			self.timerentry_vpsplugin_dontcheck_pdc = self.timer.vpsplugin_enabled
			if self.timer.vpsplugin_enabled:
				default_value = {False: "yes_safe", True: "yes"}[self.timer.vpsplugin_overwrite]

		elif config.plugins.vps.vps_default.value != "no" and self.timer.eit is not None and self.timer.name != "" and self.timer not in self.session.nav.RecordTimer.timer_list and self.timer not in self.session.nav.RecordTimer.processed_timers:
			from Vps_check import Check_PDC
			service = self.timerentry_service_ref.ref
			if service and service.flags & eServiceReference.isGroup:
				service = getBestPlayableServiceReference(service, eServiceReference())
			has_pdc, last_check, default_vps = Check_PDC.check_service(service)
			if has_pdc == 1 or default_vps == 1:
				self.timerentry_vpsplugin_dontcheck_pdc = True
				default_value = config.plugins.vps.vps_default.value

		self.timerentry_vpsplugin_enabled = ConfigSelection(choices=[("no", _("No")), ("yes_safe", _("Yes (safe mode)")), ("yes", _("Yes"))], default=default_value)

		if self.timer.vpsplugin_time is not None:
			self.timerentry_vpsplugin_time_date = ConfigDateTime(default=self.timer.vpsplugin_time, formatstring=_("%d.%B %Y"), increment=86400)
			self.timerentry_vpsplugin_time_clock = ConfigClock(default=self.timer.vpsplugin_time)
		else:
			self.timerentry_vpsplugin_time_date = ConfigDateTime(default=self.timer.begin, formatstring=_("%d.%B %Y"), increment=86400)
			self.timerentry_vpsplugin_time_clock = ConfigClock(default=self.timer.begin)
	except:
		pass
	# added by VPS-Plugin


def new_TimerEntry_createSetup(self, widget):
	if not hasattr(self, "timerentry_vpsplugin_enabled"):
		new_TimerEntry_createConfig(self)
	self._createSetup_old_rn_vps(widget)

	# added by VPS-Plugin
	self.timerVps_enabled_Entry = None
	try:
		if self.timerentry_justplay.value != "zap" and config.plugins.vps.enabled.value == True:
			self.timerVps_enabled_Entry = getConfigListEntry(_("Enable VPS"), self.timerentry_vpsplugin_enabled)
			self.list.append(self.timerVps_enabled_Entry)

			if self.timerentry_vpsplugin_enabled.value != "no":
				from Vps_check import Check_PDC, VPS_check_PDC_Screen
				service = self.timerentry_service_ref.ref
				if service and service.flags & eServiceReference.isGroup:
					service = getBestPlayableServiceReference(service, eServiceReference())

				if self.timer.eit is None or self.timer.name == "":
					if not self.timerentry_vpsplugin_dontcheck_pdc:
						self.timerentry_vpsplugin_dontcheck_pdc = True
						has_pdc, last_check, default_vps = Check_PDC.check_service(service)
						if has_pdc != 1 or Check_PDC.recheck(has_pdc, last_check):
							self.session.open(VPS_check_PDC_Screen, service, self)

					self.list.append(getConfigListEntry(_("VPS-Time (date)"), self.timerentry_vpsplugin_time_date))
					self.list.append(getConfigListEntry(_("VPS-Time (time)"), self.timerentry_vpsplugin_time_clock))

				elif not self.timerentry_vpsplugin_dontcheck_pdc:
					self.timerentry_vpsplugin_dontcheck_pdc = True
					has_pdc, last_check, default_vps = Check_PDC.check_service(service)
					if default_vps != 1 and (has_pdc != 1 or Check_PDC.recheck(has_pdc, last_check)):
						self.session.open(VPS_check_PDC_Screen, service, self, False)

					# Hilfetext
					if config.plugins.vps.infotext.value != 2:
						config.plugins.vps.infotext.value = 2
						config.plugins.vps.infotext.save()
						VPS_show_info(self.session)
	except:
		pass
	# added by VPS-Plugin
	self[widget].list = self.list
	self[widget].l.setList(self.list)


def new_TimerEntry_newConfig(self):
	self._newConfig_old_rn_vps()

	# added by VPS-Plugin
	if self["config"].getCurrent() == self.timerVps_enabled_Entry:
		if self.timerentry_vpsplugin_enabled.value == "no":
			self.timerentry_vpsplugin_dontcheck_pdc = False

		self.createSetup("config")
		self["config"].setCurrentIndex(self["config"].getCurrentIndex() + 1)
	# added by VPS-Plugin


def new_TimerEntry_keyGo(self):
	# added by VPS-Plugin
	try:
		self.timer.vpsplugin_enabled = self.timerentry_vpsplugin_enabled.value != "no"
		self.timer.vpsplugin_overwrite = self.timerentry_vpsplugin_enabled.value == "yes"
		if self.timer.vpsplugin_enabled == True:
			from Plugins.SystemPlugins.vps.Vps import vps_timers
			vps_timers.checksoon()

			if self.timer.name == "" or self.timer.eit is None:
				self.timer.vpsplugin_time = self.getTimestamp(self.timerentry_vpsplugin_time_date.value, self.timerentry_vpsplugin_time_clock.value)
				if self.timer.vpsplugin_overwrite:
					timerbegin, timerend = self.getBeginEnd()
					if (timerbegin - 60) < time() and (self.timer.vpsplugin_time - time()) > 1800:
						self.timerentry_date.value = self.timerentry_vpsplugin_time_date.value
						self.timerentry_starttime.value = self.timerentry_vpsplugin_time_clock.value
	except:
		pass
	# added by VPS-Plugin

	self._keyGo_old_rn_vps()


def new_TimerEntry_finishedChannelSelection(self, *args):
	self._finishedChannelSelection_old_rn_vps(*args)

	try:
		if self.timerentry_vpsplugin_enabled.value != "no":
			self.timerentry_vpsplugin_dontcheck_pdc = False
			self.createSetup("config")
	except:
		pass


def new_InfoBarInstantRecord_recordQuestionCallback(self, answer):
	self._recordQuestionCallback_old_rn_vps(answer)

	try:
		entry = len(self.recording) - 1
		if answer is not None and answer[1] == "event" and config.plugins.vps.instanttimer.value != "no" and entry is not None and entry >= 0:
			# If we aren't checking PDC, just put the values in directly
			if not config.plugins.vps.do_PDC_check.getValue():
				from Vps import vps_timers
				if config.plugins.vps.instanttimer.value == "yes":
					self.recording[entry].vpsplugin_enabled = True
					self.recording[entry].vpsplugin_overwrite = True
					vps_timers.checksoon()
				elif config.plugins.vps.instanttimer.value == "yes_safe":
					self.recording[entry].vpsplugin_enabled = True
					self.recording[entry].vpsplugin_overwrite = False
					vps_timers.checksoon()
			else:
				from Vps_check import VPS_check_on_instanttimer
				rec_ref = self.recording[entry].service_ref.ref
				if rec_ref and rec_ref.flags & eServiceReference.isGroup:
					rec_ref = getBestPlayableServiceReference(rec_ref, eServiceReference())
				self.session.open(VPS_check_on_instanttimer, rec_ref, self.recording[entry])
	except:
		pass


def register_vps():
	global vps_already_registered

	if vps_already_registered == False:
		RecordTimerEntry.vpsplugin_enabled = None
		RecordTimerEntry.vpsplugin_overwrite = None
		RecordTimerEntry.vpsplugin_time = None

		RecordTimer._saveTimer_old_rn_vps = RecordTimer.saveTimer
		RecordTimer.saveTimer = new_RecordTimer_saveTimer

		RecordTimer._loadTimer_old_rn_vps = RecordTimer.loadTimer
		RecordTimer.loadTimer = new_RecordTimer_loadTimer

		TimerEntry._createSetup_old_rn_vps = TimerEntry.createSetup
		TimerEntry.createSetup = new_TimerEntry_createSetup

		TimerEntry._newConfig_old_rn_vps = TimerEntry.newConfig
		TimerEntry.newConfig = new_TimerEntry_newConfig

		TimerEntry._keyGo_old_rn_vps = TimerEntry.keyGo
		TimerEntry.keyGo = new_TimerEntry_keyGo

		TimerEntry._finishedChannelSelection_old_rn_vps = TimerEntry.finishedChannelSelection
		TimerEntry.finishedChannelSelection = new_TimerEntry_finishedChannelSelection

		InfoBarInstantRecord._recordQuestionCallback_old_rn_vps = InfoBarInstantRecord.recordQuestionCallback
		InfoBarInstantRecord.recordQuestionCallback = new_InfoBarInstantRecord_recordQuestionCallback

		vps_already_registered = True
