# for localized messages
from . import _
import math
# GUI (Screens)
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Notifications import AddPopup
from ServiceReference import ServiceReference
# Timer
from enigma import eTimer, ePoint, iPlayableService, eServiceReference, eEPGCache, getDesktop
# For monitoring
from Components.ServiceEventTracker import ServiceEventTracker
# Get remaining time if timer is already active
from time import time
# Config
from Components.config import *
from Components.Sources.List import List
from Components.ConfigList import ConfigListScreen
from Components.Button import Button
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.VolumeControl import VolumeControl

zapperIconInstance = None

sz_w = getDesktop(0).size().width()

WerbeZapperIcon = """
		<screen name="WerbeZapperIndicator" title="WerbeZapper Icon" flags="wfNoBorder" position="550,50" size="150,30" zPosition="%s" backgroundColor="#31000000" >
			<widget name="icon_text" font="Regular;20" position="0,0" zPosition="1" valign="center" halign="center" size="150,30" backgroundColor="#31000000" transparent="1" />
		</screen>""" % (config.werbezapper.z.value)

WerbeZapperIcon1 = """
		<screen name="WerbeZapperIndicator" title="WerbeZapper Icon" flags="wfNoBorder" position="550,50" size="210,40" zPosition="%s" backgroundColor="#31000000" >
			<widget name="icon_text" font="Regular;17" position="0,0" zPosition="1" valign="center" halign="center" size="210,40" backgroundColor="#31000000" transparent="1" />
		</screen>""" % (config.werbezapper.z.value)

WerbeZapperIconHD = """
		<screen name="WerbeZapperIndicator" title="WerbeZapper Icon" flags="wfNoBorder" position="550,50" size="200,36" zPosition="%s" backgroundColor="#31000000" >
			<widget name="icon_text" font="Regular;22" position="0,0" zPosition="1" valign="center" halign="center" size="200,36" backgroundColor="#31000000" transparent="1" />
		</screen>""" % (config.werbezapper.z.value)

WerbeZapperIconHD1 = """
		<screen name="WerbeZapperIndicator" title="WerbeZapper Icon" flags="wfNoBorder" position="550,50" size="280,54" zPosition="%s" backgroundColor="#31000000" >
			<widget name="icon_text" font="Regular;22" position="0,0" zPosition="1" valign="center" halign="center" size="280,54" backgroundColor="#31000000" transparent="1" />
		</screen>""" % (config.werbezapper.z.value)

WerbeZapperIconFullHD = """
		<screen name="WerbeZapperIndicator" title="WerbeZapper Icon" flags="wfNoBorder" position="550,50" size="300,60" zPosition="%s" backgroundColor="#31000000" >
			<widget name="icon_text" font="Regular;40" position="0,0" zPosition="1" valign="center" halign="center" size="300,60" backgroundColor="#31000000" transparent="1" />
		</screen>""" % (config.werbezapper.z.value)

WerbeZapperIconFullHD1 = """
		<screen name="WerbeZapperIndicator" title="WerbeZapper Icon" flags="wfNoBorder" position="550,50" size="420,80" zPosition="%s" backgroundColor="#31000000" >
			<widget name="icon_text" font="Regular;34" position="0,0" zPosition="1" valign="center" halign="center" size="420,80" backgroundColor="#31000000" transparent="1" />
		</screen>""" % (config.werbezapper.z.value)


class WerbeZapperIndicator(Screen):
	def __init__(self, session, zap_time=0, zap_service=None):
		self.zap_time = zap_time
		self.zap_service = zap_service
		self.name = None
		if config.werbezapper.icon_mode.value == "0":
			if sz_w >= 1920:
				self.skin = WerbeZapperIconFullHD
			elif sz_w >= 1280:
				self.skin = WerbeZapperIconHD
			else:
				self.skin = WerbeZapperIcon
		else:
			if sz_w >= 1920:
				self.skin = WerbeZapperIconFullHD1
			elif sz_w >= 1280:
				self.skin = WerbeZapperIconHD1
			else:
				self.skin = WerbeZapperIcon1
		Screen.__init__(self, session)
		self.skinName = ["WerbeZapperIndicator" + self.__class__.__name__, "WerbeZapperIndicator"]
		self['icon_text'] = Label("")
		self.update_time = eTimer()
		self.update_time.callback.append(self.updateIcontext)
		self.onClose.append(self.__onClose)
		self.onShow.append(self.__onShow)
		config.werbezapper.x.addNotifier(self.__changePosition, False)
		config.werbezapper.y.addNotifier(self.__changePosition, False)
		self.onLayoutFinish.append(self.__changePosition)

	def __onClose(self):
		self.update_time.stop()

	def __onShow(self):
		self.update_time.stop()
		if config.werbezapper.icon_mode.value == "1" and self.zap_service is not None:
			try:
				refstr = self.zap_service.toString()
				self.name = ServiceReference(eServiceReference(refstr)).getServiceName()
			except:
				self.name = None
		if not self.update_time.isActive():
			self.updateIcontext()

	def updateIcontext(self):
		text = ""
		try:
			if self.zap_time > 0:
				remaining = int(math.floor(self.zap_time - time()))
				if remaining > 0:
					if self.name is not None:
						text += "%s\n" % self.name
					text += _("- %d:%02d min") % (remaining / 60, remaining % 60)
		except:
			text += _("Error")
		self['icon_text'].setText(text)
		self.update_time.start(1000)

	def __changePosition(self, configElement=None):
		if not self.instance is None:
			self.instance.move(ePoint(config.werbezapper.x.value, config.werbezapper.y.value))


class WerbeZapperChoiceBox(ChoiceBox):
	def __init__(self, session, title="", list=[], keys=None, selection=0, zap_time=0, zap_service=None, monitored_event=None, monitor_time=None, monitored_service=None, skin_name=[]):
		ChoiceBox.__init__(self, session, title, list, keys, selection, skin_name)

		self.update_timer = eTimer()
		self.update_timer.callback.append(self.update)

		self.zap_time = zap_time
		self.zap_service = zap_service
		self.monitored_event = monitored_event
		self.monitor_time = monitor_time
		self.monitored_service = monitored_service

		# Start timer to update the ChoiceBox every second
		self.update_timer.start(1000)
		self.setTitle(_("WerbeZapper"))
		self.update()

	def update(self):
		text = ""
		if self.monitored_event:
			name = self.monitored_event and self.monitored_event.getEventName()
			remaining = (self.monitored_event.getDuration() - (time() - self.monitored_event.getBeginTime()))
			if remaining > 0:
				text += _("Monitoring: %s (%d:%02d Min)") % (name, remaining / 60, remaining % 60)
		if self.monitor_time and not self.monitored_event:
			remaining = int(math.floor(self.monitor_time - time()))
			if remaining > 0:
				text += _("Monitoring: for service is not EPG (%d:%02d Min)") % (remaining / 60, remaining % 60)
		if self.zap_time:
			remaining = int(math.floor(self.zap_time - time()))
			if remaining > 0:
				remainstr = ("%d:%02d") % (remaining / 60, remaining % 60)
				text += "\n" + _("Zapping to service in %d:%02d Min") % (remaining / 60, remaining % 60)
				if self.zap_service is not None:
					ref_cur = self.zap_service
					if self.monitored_service is not None and self.monitored_event:
						ref_cur = self.monitored_service
					refstr = ref_cur.toString()
					zap_name = ServiceReference(eServiceReference(refstr)).getServiceName()
					text += "\n" + _("Channel: %s") % (zap_name)
		if text:
			self.setText(text)

	def setText(self, text):
		self["text"].setText(text)

	def close(self, param=None):
		self.update_timer.stop()
		ChoiceBox.close(self, param)


class WerbeZapper(Screen):
	"""Simple Plugin to automatically zap back to a Service after a given amount
		of time."""

	def __init__(self, session, servicelist, cleanupfnc=None):
		Screen.__init__(self, session)

		# Save Session&Servicelist
		self.session = session
		self.servicelist = servicelist

		# Create zap timer
		self.zap_time = None
		self.zap_timer = eTimer()
		self.zap_timer.callback.append(self.zap)

		# Create event monitoring timer
		self.monitor_timer = eTimer()
		self.monitor_timer.callback.append(self.stopMonitoring)

		# Create delay timer
		self.delay_timer = eTimer()
		self.delay_timer.callback.append(self.zappedAway)

		# Initialize services
		self.zap_service = None
		self.move_service = None
		self.root = None
		self.epg_bouquet = None

		#	Initialize monitoring
		self.monitored_service = None
		self.monitored_bouquet = None
		self.monitored_event = None
		self.monitor_time = None
		self.__event_tracker = None
		self.select = True

		# Initialize volume
		self.volume_value = -1
		self.volume_muted = False
		# Keep Cleanup
		self.cleanupfnc = cleanupfnc

	def showSelection(self):
		title = _("When zap to service?")
		val = int(config.werbezapper.duration.value)
		self.select = False
		select = 0
		if 0 < val and val < 10:
			select = val
			self.select = True
		elif not self.zap_timer.isActive():
			title += _(" Current value - %s min.") % val
		keys = []

		# Number keys
		choices = [
								(_("Custom"), 'custom'),
								('1 ' + _('min.'), 1),
								('2 ' + _('min.'), 2),
								('3 ' + _('min.'), 3),
								('4 ' + _('min.'), 4),
								('5 ' + _('min.'), 5),
								('6 ' + _('min.'), 6),
								('7 ' + _('min.'), 7),
								('8 ' + _('min.'), 8),
								('9 ' + _('min.'), 9),
							]
		keys.extend(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"])
		# Dummy entry to seperate the color keys
		choices.append(("------", 'close'))
		keys.append("")  # No key
		# Blue key - Covers the monitoring functions without closing Werbezapper
		if self.monitor_timer.isActive():
			choices.append((_("Stop monitoring"), 'stopmonitoring'))
		else:
			choices.append((_("Start monitoring"), 'startmonitoring'))
		keys.append("blue")

		# Red key - Covers all stop and close functions
		if self.zap_timer.isActive():
			if self.zap_time:
				remaining = int(math.floor(self.zap_time - time()))
				remaining = remaining if remaining > 0 else 0
				remaining /= 60
				select = int(remaining if 0 < remaining and remaining < 10 else select)
			choices.append((_("Stop timer"), 'stoptimer'))
			keys.append("red")
		else:
			choices.append(("------", 'close'))
			keys.append("")  # No key

		# Green key - Manual rezap
		if self.zap_timer.isActive():
			choices.append((_("Rezap"), 'rezap'))
			keys.append("green")
		else:
			choices.append(("------", 'close'))
			keys.append("")  # No key
		choices.append((_("Open setup"), 'setup'))
		keys.append("yellow")
		# Select Timer Length
		self.session.openWithCallback(
			self.choicesCallback,
			WerbeZapperChoiceBox,
			title,
			choices,
			keys,
			select,
			self.zap_time,
			self.zap_service,
			self.monitored_event,
			self.monitor_time,
			self.monitored_service
		)

	def choicesCallback(self, result):
		result = result and result[1]
		if result == "custom":
			from Screens.InputBox import InputBox
			from Components.Input import Input

			num = "15"
			if not self.select:
				num = str(config.werbezapper.duration.value)
			self.session.openWithCallback(
				self.inputCallback,
				InputBox,
				title=_("How many minutes to wait until zapping back?"),
				text=num,
				maxSize=False,
				type=Input.NUMBER
			)
			return

		elif result == "startmonitoring":
			self.startMonitoring()

		elif result == "stopmonitoring":
			self.stopMonitoring()

		elif result == "rezap":
			self.stopTimer()
			self.zap()

		elif result == "stoptimer":
			self.stopTimer()

		elif result == "reopen":
			self.showSelection()

		elif result == "setup":
			self.session.open(WerbezapperSettings)
		elif result == "close":
			pass

		elif isinstance(result, int):
			self.startTimer(result)

		self.cleanup()

	def inputCallback(self, result):
		if result:
			self.startTimer(int(result))
		else:
			# Clean up if possible
			self.cleanup()

	def startMonitoring(self, notify=True):
		# Stop active zap timer
		self.stopTimer()

		# Get current service and event
		service = self.session.nav.getCurrentService()
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		self.monitored_service = ref

		# Notify us on new services
		# ServiceEventTracker will remove itself on close
		if not self.__event_tracker:
			self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evStart: self.serviceStarted,
			})

		# Get event information
		info = service and service.info()
		event = info and info.getEvent(0)
		if not event:
			# Alternative to get the current event
			epg = eEPGCache.getInstance()
			event = ref and ref.valid() and epg.lookupEventTime(ref, -1)
		if event:
			# Set monitoring end time
			self.monitored_event = event
			duration = event.getDuration() - (time() - event.getBeginTime())
			self.monitored_bouquet = self.servicelist.getRoot()
			self.monitor_timer.startLongTimer(int(duration))
			self.monitor_time = None
			if notify:
				name = event and event.getEventName()
				AddPopup(
									_("WerbeZapper...\nMonitoring started\n%s") % (name),
									MessageBox.TYPE_INFO,
									3,
									"WerbeZapperMonitoringStarted"
								)
		else:
			duration = int(config.werbezapper.duration_not_event.value)
			self.monitor_time = time() + (duration * 60)
			self.monitored_bouquet = self.servicelist.getRoot()
			self.monitor_timer.startLongTimer(duration * 60)
			self.monitored_event = None
			if notify:
				AddPopup(
									_("WerbeZapper...\nMonitoring started for service is not EPG.\nDuration %d Min.") % (duration),
									MessageBox.TYPE_INFO,
									5,
									"WerbeZapperMonitoringStartedUnlimited"
								)

	def stopMonitoring(self, notify=True):
		# Stop active zap timer
		self.stopTimer()
		self.monitor_timer.stop()
		if notify:
			# Notify the User that the monitoring is ending
			name = ""
			if self.monitored_event:
				name = self.monitored_event and self.monitored_event.getEventName()
			elif self.monitor_time:
				name = _("Service is not EPG")
			AddPopup(
								_("WerbeZapper\nMonitoring ends\n%s") % (name),
								MessageBox.TYPE_INFO,
								3,
								"WerbeZapperMonitoringStopped"
							)

		self.monitored_service = None
		self.monitored_event = None
		self.monitor_time = None
		self.monitored_bouquet = None

	def serviceStarted(self):
		# Verify monitoring is active
		if self.monitor_timer.isActive():
			# Verify there is no active zap timer
			if not self.zap_timer.isActive():
				# Is the zap away check already running
				if not self.delay_timer.isActive():
					# Delay the zap away check only once
					self.delay_timer.startLongTimer(3)

	def zappedAway(self):
		# Verify that the currently played service has changed
		# Avoid that we trigger on a background recording or streaming service
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		if ref and self.monitored_service and self.monitored_service != ref:
			# Start zap timer
			self.startTimer(zapto=self.monitored_service)

	def addStartTimer(self, duration=0):
		self.stopMonitoring(notify=False)
		self.zap_service = self.servicelist.getCurrentSelection()
		self.epg_bouquet = self.servicelist.getRoot()
		if duration > 0:
			config.werbezapper.channelselection_duration.value = duration
			config.werbezapper.channelselection_duration.save()
			self.zap_time = time() + (int(duration * 60))
			self.zap_timer.startLongTimer(int(duration * 60))
			if config.werbezapper.icon_timer.value:
				self.StartIndicator()

	def startTimer(self, duration=0, notify=True, zapto=None):
		if self.zap_timer.isActive():
			self.stopTimer()
		if duration > 0:
			# Save the last selected zap time for reusing it later
			config.werbezapper.duration.value = duration
			config.werbezapper.duration.save()
		else:
			# Reuse last duration
			duration = int(config.werbezapper.duration.value)

		# Keep any service related information (zap_service might not equal move_service -> subservices)
		self.zap_service = self.session.nav.getCurrentlyPlayingServiceReference()
		if zapto is not None or self.monitored_service is not None:
			self.zap_service = self.monitored_service
		self.epg_bouquet = self.servicelist.getRoot()
		self.move_service = None if zapto else self.servicelist.getCurrentSelection()
		ref_cur = self.zap_service
		refstr = ref_cur.toString()
		zap_name = ServiceReference(eServiceReference(refstr)).getServiceName()
		if config.werbezapper.preserve_volume.value:
			WZ_vctrl = VolumeControl.instance
			if WZ_vctrl:
				self.volume_value = WZ_vctrl.volctrl.getVolume()
				self.volume_muted = WZ_vctrl.volctrl.isMuted()

		# Start Timer
		self.zap_time = time() + (duration * 60)
		self.zap_timer.startLongTimer(int(duration * 60))

		if notify:
			AddPopup(_("Zapping back %s in %d Min") % (zap_name, duration), MessageBox.TYPE_INFO, 3, "WerbeZapperZapStarted")
		if config.werbezapper.icon_timer.value:
			self.StartIndicator()

	def stopTimer(self):
		# Stop Timer
		self.zap_timer.stop()
		self.zap_time = None
		self.StopIndicator()

	def zap(self, notify=True):
		import Screens.Standby
		standby = False
		if Screens.Standby.inStandby:
			standby = True
		wakeup = config.werbezapper.standby.value
		if self.zap_service and (not standby or (standby and wakeup and not self.monitor_timer.isActive())):
			from ServiceReference import ServiceReference
			from enigma import iPlayableService, eServiceReference
			ref_cur = self.zap_service
			refstr = ref_cur.toString()
			zap_name = ServiceReference(eServiceReference(refstr)).getServiceName()
			ref_now = self.session.nav.getCurrentlyPlayingServiceReference()
			if notify:
				if ref_now and ref_now != self.zap_service:
					AddPopup(_("Zapping to %s") % (zap_name), MessageBox.TYPE_INFO, 3, "WerbeZapperZapBack")
			self.root = self.servicelist.getRoot()
			if self.root:
				if self.monitor_timer.isActive():
					if self.monitored_bouquet is not None:
						self.epg_bouquet = self.monitored_bouquet
				if self.root != self.epg_bouquet:
					self.servicelist.clearPath()
					if self.servicelist.bouquet_root != self.epg_bouquet:
						self.servicelist.enterPath(self.servicelist.bouquet_root)
					self.servicelist.enterPath(self.epg_bouquet)
				self.servicelist.setCurrentSelection(self.zap_service)
				self.servicelist.zap()
			if standby and wakeup:
				Screens.Standby.inStandby.prev_running_service = self.zap_service
				Screens.Standby.inStandby.Power()
			ref_cur = self.session.nav.getCurrentlyPlayingServiceReference()
			if ref_cur and ref_cur != self.zap_service:
				self.session.nav.playService(self.zap_service)
			if config.werbezapper.preserve_volume.value:
				WZ_vctrl = VolumeControl.instance
				if WZ_vctrl and self.volume_value != -1:
					WZ_vctrl.volctrl.setVolume(self.volume_value, self.volume_value)
					if WZ_vctrl.volctrl.isMuted() and not self.volume_muted:
						WZ_vctrl.volMute()

		# Cleanup if end timer is not running
		if not self.monitor_timer.isActive():
			# Reset services
			self.zap_service = None
			self.move_service = None
			self.root = None
			self.epg_bouquet = None
			self.volume_value = -1
			self.volume_muted = False
		self.StopIndicator()

	def cleanup(self):
		# Clean up if no timer is running
		if self.monitor_timer and not self.monitor_timer.isActive() \
			and self.zap_timer and not self.zap_timer.isActive():
			if self.cleanupfnc:
				self.cleanupfnc()

	def shutdown(self):
		self.zap_timer.callback.remove(self.zap)
		self.zap_timer = None
		self.monitor_timer.callback.remove(self.stopMonitoring)
		self.monitor_timer = None

	def StartIndicator(self):
		global zapperIconInstance
		if zapperIconInstance is None:
			zapperIconInstance = self.session.instantiateDialog(WerbeZapperIndicator, self.zap_time, self.zap_service)
			zapperIconInstance.show()

	def StopIndicator(self):
		global zapperIconInstance
		if zapperIconInstance is not None:
			zapperIconInstance.update_time.stop()
			zapperIconInstance.hide()
			zapperIconInstance = None


class WerbezapperSettings(Screen, ConfigListScreen):
	if sz_w < 1920:
		skin = """<screen position="center,center" size="610,364" title="WerbezapperSettings" backgroundColor="#31000000" >
			<widget name="config" position="10,10" size="595,314" zPosition="1" transparent="0" backgroundColor="#31000000" font="Regular;18" scrollbarMode="showOnDemand" />
			<widget name="key_red" position="10,328" zPosition="2" size="250,25" halign="center" font="Regular;20" transparent="1" foregroundColor="red" />
			<widget name="key_green" position="355,328" zPosition="2" size="250,25" halign="center" font="Regular;20" transparent="1" foregroundColor="green" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WerbeZapper/red.png" position="10,320" size="250,42" zPosition="1" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WerbeZapper/green.png" position="350,320" size="250,42" zPosition="1" alphatest="on" />
		</screen>"""
	else:
		skin = """<screen position="center,center" size="900,525" title="WerbezapperSettings" backgroundColor="#31000000" >
			<widget name="config" position="10,10" size="880,465" zPosition="1" transparent="0" backgroundColor="#31000000" itemHeight="37" font="Regular;27" scrollbarMode="showOnDemand" />
			<widget name="key_red" position="10,486" zPosition="2" size="250,28" halign="center" font="Regular;25" transparent="1" foregroundColor="red" />
			<widget name="key_green" position="272,486" zPosition="2" size="250,28" halign="center" font="Regular;25" transparent="1" foregroundColor="green" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WerbeZapper/red.png" position="10,480" size="250,42" zPosition="1" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WerbeZapper/green.png" position="272,480" size="250,42" zPosition="1" alphatest="on" />
		</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.setTitle(_("WerbeZapper Setup"))
		self['key_red'] = Button(_('Cancel'))
		self['key_green'] = Button(_('Save'))
		self['actions'] = ActionMap(['SetupActions', 'ColorActions'], {'green': self.save, 'ok': self.save, 'red': self.exit, 'cancel': self.exit}, -2)
		ConfigListScreen.__init__(self, [])
		self.initConfig()
		self.createSetup()

	def initConfig(self):
		def getPrevValues(section):
			res = {}
			for (key, val) in section.content.items.items():
				if isinstance(val, ConfigSubsection):
					res[key] = getPrevValues(val)
				else:
					res[key] = val.value
			return res
		self.WERB = config.werbezapper
		self.prev_values = getPrevValues(self.WERB)
		self.cfg_extmenu = getConfigListEntry(_('Show \"Start / Stop monitoring\" in extensions menu'), config.werbezapper.monitoring_extmenu)
		self.cfg_channelselection = getConfigListEntry(_("Show plugin in channel selection context menu"), config.werbezapper.add_to_channelselection)
		self.cfg_channelselection_step = getConfigListEntry(_("Slider step size (1 - 20 mins)"), config.werbezapper.channelselection_duration_stepsize)
		self.cfg_standby = getConfigListEntry(_('Wakeup receiver from standby for zap timer'), config.werbezapper.standby)
		self.cfg_hotkey = getConfigListEntry(_('\"Werbezapper\" quick button'), config.werbezapper.hotkey)
		self.cfg_volume = getConfigListEntry(_('Preserve volume'), config.werbezapper.preserve_volume)
		self.cfg_no_event = getConfigListEntry(_('Monitoring duration for service if not EPG'), config.werbezapper.duration_not_event)
		self.cfg_icon_timer = getConfigListEntry(_('Show indicator zap time in window'), config.werbezapper.icon_timer)
		self.cfg_icon_mode = getConfigListEntry(_('Indicator mode'), config.werbezapper.icon_mode)
		self.cfg_x = getConfigListEntry(_('X position'), config.werbezapper.x)
		self.cfg_y = getConfigListEntry(_('Y position'), config.werbezapper.y)
		self.cfg_z = getConfigListEntry(_('Z position (priority of srceen)'), config.werbezapper.z)

	def createSetup(self):
		list = []
		#list.append(self.cfg_hotkey)
		list.append(self.cfg_extmenu)
		list.append(self.cfg_channelselection)
		if config.werbezapper.add_to_channelselection.value:
			list.append(self.cfg_channelselection_step)
		list.append(self.cfg_standby)
		list.append(self.cfg_volume)
		list.append(self.cfg_no_event)
		list.append(self.cfg_icon_timer)
		if config.werbezapper.icon_timer.value:
			list.append(self.cfg_icon_mode)
			list.append(self.cfg_x)
			list.append(self.cfg_y)
			list.append(self.cfg_z)
		self["config"].list = list
		self["config"].l.setList(list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def save(self):
		self.WERB.save()
		self.close()

	def exit(self):
		def setPrevValues(section, values):
			for (key, val) in section.content.items.items():
				value = values.get(key, None)
				if value is not None:
					if isinstance(val, ConfigSubsection):
						setPrevValues(val, value)
					else:
						val.value = value
		setPrevValues(self.WERB, self.prev_values)
		self.save()
