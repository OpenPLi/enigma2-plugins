from __future__ import print_function

# for localized messages
from . import _

# Config
from Components.config import config, ConfigYesNo, ConfigNumber, ConfigSelectionNumber, \
	ConfigSelection, ConfigSubsection, ConfigClock, ConfigText, ConfigInteger, ConfigSubDict, ConfigEnableDisable
from enigma import eServiceReference, iPlayableService, eTimer
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InfoBar import InfoBar
from Components.Label import Label
from Components.ActionMap import ActionMap
from ServiceReference import ServiceReference
from Screens.ChannelSelection import ChannelContextMenu, OFF, MODE_TV, service_types_tv
from Components.ChoiceList import ChoiceEntryComponent
from Tools.BoundFunction import boundFunction
import EpgLoadSaveRefresh
import os
# Plugin
from EPGRefresh import epgrefresh
from EPGRefreshConfiguration import EPGRefreshConfiguration
from EPGRefreshService import EPGRefreshService

_session = None
# Plugins
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor


# Calculate default begin/end
from time import time, localtime, mktime

#Configuration
config.plugins.epgrefresh = ConfigSubsection()
config.plugins.epgrefresh.enabled = ConfigYesNo(default = False)
config.plugins.epgrefresh.begin = ConfigClock(default = ((20*60) + 15) * 60)
config.plugins.epgrefresh.end = ConfigClock(default = ((6*60) + 30) * 60)
config.plugins.epgrefresh.interval_seconds = ConfigNumber(default = 120)
config.plugins.epgrefresh.delay_standby = ConfigNumber(default = 10)
config.plugins.epgrefresh.inherit_autotimer = ConfigYesNo(default = False)
config.plugins.epgrefresh.afterevent = ConfigYesNo(default = False)
config.plugins.epgrefresh.force = ConfigYesNo(default = False)
config.plugins.epgrefresh.enablemessage = ConfigYesNo(default = True)
config.plugins.epgrefresh.wakeup = ConfigYesNo(default = False)
config.plugins.epgrefresh.start_on_mainmenu = ConfigYesNo(default = False)
config.plugins.epgrefresh.lastscan = ConfigNumber(default = 0)
config.plugins.epgrefresh.timeout_shutdown = ConfigInteger(default = 2, limits= (2, 30))
config.plugins.epgrefresh.parse_autotimer = ConfigYesNo(default = False)
config.plugins.epgrefresh.adapter = ConfigSelection(choices = [
		("main", _("Main Picture")),
		("pip", _("Picture in Picture")),
		("pip_hidden", _("Picture in Picture (hidden)")),
		("record", _("Fake recording")),
	], default = "main"
)
config.plugins.epgrefresh.add_to_refresh = ConfigSelection(choices = [
		("0", _("nowhere")),
		("1", _("event info")),
		("2", _("channel selection")),
		("3", _("event info / channel selection")),
	], default = "1"
)
config.plugins.epgrefresh.show_in_extensionsmenu = ConfigYesNo(default = False)
config.plugins.epgrefresh.show_help = ConfigYesNo(default = True)
config.plugins.epgrefresh.save_epg = ConfigYesNo(default = False)
config.plugins.epgrefresh.setup_epg = ConfigSelection(choices = [("1", _("Press OK"))], default = "1")
config.plugins.epgrefresh.day_profile = ConfigSelection(choices = [("1", _("Press OK"))], default = "1")
config.plugins.epgrefresh.skipProtectedServices = ConfigSelection(choices = [
		("bg_only", _("Background only")),
		("always", _("Foreground also")),
	], default = "bg_only"
)

# convert previous parameters
config.plugins.epgrefresh.background = ConfigYesNo(default = False)
if config.plugins.epgrefresh.background.value:
	config.plugins.epgrefresh.adapter.value = "pip_hidden"
	config.plugins.epgrefresh.background.value = False
	config.plugins.epgrefresh.save()
config.plugins.epgrefresh.interval = ConfigNumber(default = 2)
if config.plugins.epgrefresh.interval.value != 2:
	config.plugins.epgrefresh.interval_seconds.value = config.plugins.epgrefresh.interval.value * 60
	config.plugins.epgrefresh.interval.value = 2
	config.plugins.epgrefresh.save()

config.plugins.epgrefresh_extra = ConfigSubsection()
config.plugins.epgrefresh_extra.cacheloadsched = ConfigYesNo(default = False)
config.plugins.epgrefresh_extra.cachesavesched = ConfigYesNo(default = False)
def EpgCacheLoadSchedChanged(configElement):
	EpgLoadSaveRefresh.EpgCacheLoadCheck()
def EpgCacheSaveSchedChanged(configElement):
	EpgLoadSaveRefresh.EpgCacheSaveCheck()
config.plugins.epgrefresh_extra.cacheloadsched.addNotifier(EpgCacheLoadSchedChanged)
config.plugins.epgrefresh_extra.cachesavesched.addNotifier(EpgCacheSaveSchedChanged)
config.plugins.epgrefresh_extra.cacheloadtimer = ConfigSelectionNumber(default = 24, stepwidth = 1, min = 1, max = 24, wraparound = True)
config.plugins.epgrefresh_extra.cachesavetimer = ConfigSelectionNumber(default = 24, stepwidth = 1, min = 1, max = 24, wraparound = True)
config.plugins.epgrefresh_extra.manual_save = ConfigSelection(choices = [("1", _("Press OK"))], default = "1")
config.plugins.epgrefresh_extra.manual_load = ConfigSelection(choices = [("1", _("Press OK"))], default = "1")
config.plugins.epgrefresh_extra.manual_reload = ConfigSelection(choices = [("1", _("Press OK"))], default = "1")
config.plugins.epgrefresh_extra.main_menu = ConfigYesNo(default = False)
config.plugins.epgrefresh_extra.epgcachepath = ConfigText(default = "/etc/enigma2/", fixed_size=False)
config.plugins.epgrefresh_extra.epgcachefilename = ConfigText(default="epg", fixed_size=False)
config.plugins.epgrefresh_extra.save_backup = ConfigYesNo(default = False)
config.plugins.epgrefresh_extra.restore_backup = ConfigSelection(choices = [("1", _("Press OK"))], default = "1")
config.plugins.epgrefresh_extra.autorestore_backup = ConfigYesNo(default = False)
config.plugins.epgrefresh_extra.add_ruepg = ConfigYesNo(default = False)
config.plugins.epgrefresh_extra.load_ruepg = ConfigSelection(choices = [("1", _("Press OK"))], default = "1")
config.plugins.epgrefresh_extra.show_autozap = ConfigYesNo(default = False)
config.plugins.epgrefresh_extra.timeout_autozap = ConfigInteger(default = 15, limits= (10, 90))
config.plugins.epgrefresh_extra.day_refresh = ConfigSubDict()
for i in range(7):
	config.plugins.epgrefresh_extra.day_refresh[i] = ConfigEnableDisable(default = True)

#pragma mark - Workaround for unset clock
from enigma import eDVBLocalTimeHandler

def timeCallback(isCallback=True):
	"""Time Callback/Autostart management."""
	thInstance = eDVBLocalTimeHandler.getInstance()
	if isCallback:
		# NOTE: this assumes the clock is actually ready when called back
		# this may not be true, but we prefer silently dying to waiting forever
		thInstance.m_timeUpdated.get().remove(timeCallback)
	elif not thInstance.ready():
		thInstance.m_timeUpdated.get().append(timeCallback)
		return

	if config.plugins.epgrefresh.wakeup.value:
		now = localtime()
		begin = int(mktime(
			(now.tm_year, now.tm_mon, now.tm_mday,
			config.plugins.epgrefresh.begin.value[0],
			config.plugins.epgrefresh.begin.value[1],
			0, now.tm_wday, now.tm_yday, now.tm_isdst)
		))
		# booted +- 6min from begin of timespan
		cur_day = int(now.tm_wday)
		if abs(time() - begin) < 360 and config.plugins.epgrefresh_extra.day_refresh[cur_day].value:
			from Tools.Notifications import AddNotificationWithCallback
			from Tools.BoundFunction import boundFunction
			# XXX: we use a notification because this will be suppressed otherwise
			AddNotificationWithCallback(
				boundFunction(standbyQuestionCallback, epgrefresh.session),
				MessageBox,
				_("This might have been an automated bootup to refresh the EPG. For this to happen it is recommended to put the receiver to Standby.\nDo you want to do this now?"),
				timeout = 30
			)
	epgrefresh.start()

#pragma mark - Help
try:
	from Plugins.SystemPlugins.MPHelp import registerHelp, XMLHelpReader
	from Tools.Directories import resolveFilename, SCOPE_PLUGINS
	reader = XMLHelpReader(resolveFilename(SCOPE_PLUGINS, "Extensions/EPGRefresh/mphelp.xml"))
	epgrefreshHelp = registerHelp(*reader)
except Exception as e:
	print("[EPGRefresh] Unable to initialize MPHelp:", e,"- Help not available!")
	epgrefreshHelp = None

class AutoZap(Screen):
	skin="""
		<screen flags="wfNoBorder" position="center,25" size="500,30" title="AutoZap" backgroundColor="#64121214">
			<widget name="wohin" position="0,0" size="500,30" font="Regular;20" foregroundColor="foreground" transparent="1" zPosition="1" halign="center" valign="center">
				<convert type="ConditionalShowHide">Blink</convert>
			</widget>
		</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self["wohin"] = Label(_("AutoZap"))
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.ende,
			"cancel": self.ende
		}, -1)
		self.AutoZap = eTimer()
		self.AutoZap.callback.append(self.zapForRefresh)
		self.AZpos = myServicelist.servicelist.getCurrentIndex()
		self.onLayoutFinish.append(self.firstStart)

	def firstStart(self):
		myServicelist.servicelist.moveToIndex(0)
		myServicelist.zap()
		srvName = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference()).getServiceName()
		srvName = srvName.replace('\xc2\x86', '').replace('\xc2\x87', '')
		self["wohin"].setText(srvName + _("   (AutoZap)"))
		delay = config.plugins.epgrefresh_extra.timeout_autozap.value
		self.AutoZap.start(int(delay * 1000))

	def ende(self):
		myServicelist.servicelist.moveToIndex(self.AZpos)
		myServicelist.zap()
		self.AutoZap.stop()
		try:
			from enigma import eEPGCache
			epgcache = eEPGCache.getInstance()
			epgcache.save()
		except:
			pass
		self.close()

	def zapForRefresh(self):
		myServicelist.moveDown()
		NewService = myServicelist.getCurrentSelection()
		if (NewService.flags & 7) == 7:
			myServicelist.enterPath(NewService)
		elif not (NewService.flags & eServiceReference.isMarker):
			myServicelist.zap()
			srvName = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference()).getServiceName()
			srvName = srvName.replace('\xc2\x86', '').replace('\xc2\x87', '')
			self["wohin"].setText(srvName + _("   (AutoZap)"))

def standbyQuestionCallback(session, res = None):
	if res:
		from Screens import Standby
		if Standby.inStandby is None:
			session.open(Standby.Standby)

def autostart(reason, session=None, **kwargs):
	global _session
	if reason == 0 and _session is None:
		if session is not None:
			epgrefresh.session = session
			_session = session
			if config.plugins.epgrefresh.enabled.value:
				timeCallback(isCallback=False)
			if config.plugins.epgrefresh_extra.autorestore_backup.value:
				restore_backup = config.misc.epgcache_filename.value + ".backup"
				if os.path.exists(restore_backup):
					try:
						os.system("cp -f %s %s" % (restore_backup, config.misc.epgcache_filename.value ))
						if os.path.exists(config.misc.epgcache_filename.value): 
							os.chmod("%s" % (config.misc.epgcache_filename.value), 0644)
					except:
						pass
			if os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/OpenWebif/pluginshook.src"):
				try:
					from EPGRefreshResource import \
							EPGRefreshStartRefreshResource, \
							EPGRefreshAddRemoveServiceResource, \
							EPGRefreshListServicesResource, \
							EPGRefreshChangeSettingsResource, \
							EPGRefreshSettingsResource, \
							EPGRefreshPreviewServicesResource, \
							API_VERSION
					root = EPGRefreshListServicesResource()
					root.putChild("refresh", EPGRefreshStartRefreshResource())
					root.putChild("add", EPGRefreshAddRemoveServiceResource(EPGRefreshAddRemoveServiceResource.TYPE_ADD))
					root.putChild("del", EPGRefreshAddRemoveServiceResource(EPGRefreshAddRemoveServiceResource.TYPE_DEL))
					root.putChild("set", EPGRefreshChangeSettingsResource())
					root.putChild("get", EPGRefreshSettingsResource())
					root.putChild("preview", EPGRefreshPreviewServicesResource())
					from Plugins.Extensions.WebInterface.WebChilds.Toplevel import addExternalChild
					addExternalChild( ("epgrefresh", root, "EPGRefresh-Plugin", API_VERSION) )
					print("[EPGRefresh] Use OpenWebif")
				except:
					print("[EPGRefresh] Error use OpenWebif")
	elif reason == 1:
		epgrefresh.stop()

def getNextWakeup():
	# Return invalid time if not automatically refreshing
	if not config.plugins.epgrefresh.enabled.value:
		return -1
	if not config.plugins.epgrefresh.wakeup.value:
		return -1

	now = localtime()
	begin = int(mktime(
		(now.tm_year, now.tm_mon, now.tm_mday,
		config.plugins.epgrefresh.begin.value[0],
		config.plugins.epgrefresh.begin.value[1],
		0, now.tm_wday, now.tm_yday, now.tm_isdst)
	))
	wakeup_day = WakeupDayOfWeek()
	# old config
	if wakeup_day == -1:
		if begin > time():
			return begin
		return begin+86400
	# now config
	current_day = int(now.tm_wday)
	if begin > time():
		if config.plugins.epgrefresh_extra.day_refresh[current_day].value:
			return begin
	return begin+86400*wakeup_day

def WakeupDayOfWeek():
	start_day = -1
	try:
		now = localtime()
		cur_day = int(now.tm_wday)
	except:
		cur_day = -1
	if cur_day == 0:
		if config.plugins.epgrefresh_extra.day_refresh[1].value:
			start_day = 1
		else:
			if config.plugins.epgrefresh_extra.day_refresh[2].value:
				start_day = 2
			else:
				if config.plugins.epgrefresh_extra.day_refresh[3].value:
					start_day = 3
				else:
					if config.plugins.epgrefresh_extra.day_refresh[4].value:
						start_day = 4
					else:
						if config.plugins.epgrefresh_extra.day_refresh[5].value:
							start_day = 5
						else:
							if config.plugins.epgrefresh_extra.day_refresh[6].value:
								start_day = 6
							else:
								if config.plugins.epgrefresh_extra.day_refresh[0].value:
									start_day = 7
	elif cur_day == 1:
		if config.plugins.epgrefresh_extra.day_refresh[2].value:
			start_day = 1
		else:
			if config.plugins.epgrefresh_extra.day_refresh[3].value:
				start_day = 2
			else:
				if config.plugins.epgrefresh_extra.day_refresh[4].value:
					start_day = 3
				else:
					if config.plugins.epgrefresh_extra.day_refresh[5].value:
						start_day = 4
					else:
						if config.plugins.epgrefresh_extra.day_refresh[6].value:
							start_day = 5
						else:
							if config.plugins.epgrefresh_extra.day_refresh[0].value:
								start_day = 6
							else:
								if config.plugins.epgrefresh_extra.day_refresh[1].value:
									start_day = 7
	elif cur_day == 2:
		if config.plugins.epgrefresh_extra.day_refresh[3].value:
			start_day = 1
		else:
			if config.plugins.epgrefresh_extra.day_refresh[4].value:
				start_day = 2
			else:
				if config.plugins.epgrefresh_extra.day_refresh[5].value:
					start_day = 3
				else:
					if config.plugins.epgrefresh_extra.day_refresh[6].value:
						start_day = 4
					else:
						if config.plugins.epgrefresh_extra.day_refresh[0].value:
							start_day = 5
						else:
							if config.plugins.epgrefresh_extra.day_refresh[1].value:
								start_day = 6
							else:
								if config.plugins.epgrefresh_extra.day_refresh[2].value:
									start_day = 7
	elif cur_day == 3:
		if config.plugins.epgrefresh_extra.day_refresh[4].value:
			start_day = 1
		else:
			if config.plugins.epgrefresh_extra.day_refresh[5].value:
				start_day = 2
			else:
				if config.plugins.epgrefresh_extra.day_refresh[6].value:
					start_day = 3
				else:
					if config.plugins.epgrefresh_extra.day_refresh[0].value:
						start_day = 4
					else:
						if config.plugins.epgrefresh_extra.day_refresh[1].value:
							start_day = 5
						else:
							if config.plugins.epgrefresh_extra.day_refresh[2].value:
								start_day = 6
							else:
								if config.plugins.epgrefresh_extra.day_refresh[3].value:
									start_day = 7
	elif cur_day == 4:
		if config.plugins.epgrefresh_extra.day_refresh[5].value:
			start_day = 1
		else:
			if config.plugins.epgrefresh_extra.day_refresh[6].value:
				start_day = 2
			else:
				if config.plugins.epgrefresh_extra.day_refresh[0].value:
					start_day = 3
				else:
					if config.plugins.epgrefresh_extra.day_refresh[1].value:
						start_day = 4
					else:
						if config.plugins.epgrefresh_extra.day_refresh[2].value:
							start_day = 5
						else:
							if config.plugins.epgrefresh_extra.day_refresh[3].value:
								start_day = 6
							else:
								if config.plugins.epgrefresh_extra.day_refresh[4].value:
									start_day = 7
	elif cur_day == 5:
		if config.plugins.epgrefresh_extra.day_refresh[6].value:
			start_day = 1
		else:
			if config.plugins.epgrefresh_extra.day_refresh[0].value:
				start_day = 2
			else:
				if config.plugins.epgrefresh_extra.day_refresh[1].value:
					start_day = 3
				else:
					if config.plugins.epgrefresh_extra.day_refresh[2].value:
						start_day = 4
					else:
						if config.plugins.epgrefresh_extra.day_refresh[3].value:
							start_day = 5
						else:
							if config.plugins.epgrefresh_extra.day_refresh[4].value:
								start_day = 6
							else:
								if config.plugins.epgrefresh_extra.day_refresh[5].value:
									start_day = 7
	elif cur_day == 6:
		if config.plugins.epgrefresh_extra.day_refresh[0].value:
			start_day = 1
		else:
			if config.plugins.epgrefresh_extra.day_refresh[1].value:
				start_day = 2
			else:
				if config.plugins.epgrefresh_extra.day_refresh[2].value:
					start_day = 3
				else:
					if config.plugins.epgrefresh_extra.day_refresh[3].value:
						start_day = 4
					else:
						if config.plugins.epgrefresh_extra.day_refresh[4].value:
							start_day = 5
						else:
							if config.plugins.epgrefresh_extra.day_refresh[5].value:
								start_day = 6
							else:
								if config.plugins.epgrefresh_extra.day_refresh[6].value:
									start_day = 7
	return start_day


# Mainfunction
def main(session, **kwargs):
	epgrefresh.stop()
	session.openWithCallback(
		doneConfiguring,
		EPGRefreshConfiguration
	)

def doneConfiguring(session, **kwargs):
	if config.plugins.epgrefresh.enabled.value:
		epgrefresh.start(session)

# Eventinfo
def eventinfo(session, servicelist, **kwargs):
	ref = session.nav.getCurrentlyPlayingServiceReference()
	if not ref:
		return
	sref = ref.toString()
	# strip all after last :
	pos = sref.rfind(':')
	if pos != -1:
		sref = sref[:pos+1]
	try:
		epgrefresh.services[0].add(EPGRefreshService(str(sref), None))
	except:
		pass
	try:
		epgrefresh.saveConfiguration()
	except:
		pass


def extensionsmenu(session, **kwargs):
	main(session, **kwargs)

def autostart_ChannelContextMenu(session, **kwargs):
	EPGRefreshChannelContextMenuInit()

baseChannelContextMenu__init__ = None
def EPGRefreshChannelContextMenuInit():
	global baseChannelContextMenu__init__
	if baseChannelContextMenu__init__ is None:
		baseChannelContextMenu__init__ = ChannelContextMenu.__init__
	ChannelContextMenu.__init__ = EPGRefreshChannelContextMenu__init__
	ChannelContextMenu.addtoEPGRefresh = addtoEPGRefresh

def EPGRefreshChannelContextMenu__init__(self, session, csel):
	baseChannelContextMenu__init__(self, session, csel)
	if csel.mode == MODE_TV:
		current = csel.getCurrentSelection()
		current_root = csel.getRoot()
		current_sel_path = current.getPath()
		current_sel_flags = current.flags
		inBouquetRootList = current_root and current_root.getPath().find('FROM BOUQUET "bouquets.') != -1 #FIXME HACK
		inBouquet = csel.getMutableList() is not None
		isPlayable = not (current_sel_flags & (eServiceReference.isMarker|eServiceReference.isDirectory))
		if csel.bouquet_mark_edit == OFF and not csel.movemode and current and current.valid():
			if isPlayable:
				profile = config.plugins.epgrefresh.add_to_refresh.value
				if profile == "2" or profile == "3":
					callFunction = self.addtoEPGRefresh
					self["menu"].list.insert(2, ChoiceEntryComponent(text = (_("add service to EPGRefresh"), boundFunction(callFunction,1))))
				else:
					pass

def addtoEPGRefresh(self, add):
	ref = self.csel.servicelist.getCurrent()
	if not ref:
		return
	sref = ref.toString()
	# strip all after last :
	pos = sref.rfind(':')
	if pos != -1:
		sref = sref[:pos+1]
	try:
		epgrefresh.services[0].add(EPGRefreshService(str(sref), None))
	except:
		pass
	try:
		epgrefresh.saveConfiguration()
	except:
		pass
	self.close()

def main_menu(menuid, **kwargs):
	if menuid == "mainmenu" and config.plugins.epgrefresh_extra.main_menu.value:
		return [(_("Manual EPG"), manual_epg, "Manual_Epg", 45)]
	return []

def manualrefresh_menu(menuid, **kwargs):
	if menuid == "mainmenu" and epgrefresh.isRunning():
		return [(_("Stop Running EPG-refresh"), stop_Running, "stop_EPG-refresh", 10)]
	elif menuid == "mainmenu" and config.plugins.epgrefresh.start_on_mainmenu.value and not epgrefresh.isRunning():
		return [(_("EPG-refresh now"), start_Running, "start_EPG-refresh", 10)]
	return []

def stop_Running(session, **kwargs):
	if not epgrefresh.isRunning():
		return True
	epgrefresh.showPendingServices(session)

def start_Running(session, **kwargs):
	if epgrefresh.isRunning():
		return True
	epgrefresh.forceRefresh(session, dontshutdown=True)

myServicelist = None
def autozap(session, servicelist, **kwargs):
	global myServicelist
	if servicelist:
		myServicelist = servicelist
		session.open(AutoZap)

def manual_epg(session, **kwargs):
	from EPGSaveLoadConfiguration import ManualEPGlist 
	session.open(ManualEPGlist)

def housekeepingExtensionsmenu(el):
	if el.value:
		plugins.addPlugin(extDescriptor)
	else:
		try:
			plugins.removePlugin(extDescriptor)
		except ValueError as ve:
			print("[EPGRefresh] housekeepingExtensionsmenu got confused, tried to remove non-existant plugin entry... ignoring.")

def AutozapExtensionsmenu(el):
	if el.value:
		plugins.addPlugin(autozapDescriptor)
	else:
		try:
			plugins.removePlugin(autozapDescriptor)
		except ValueError as ve:
			print("[EPGRefresh] housekeepingExtensionsmenu got confused, tried to remove non-existant plugin entry... ignoring.")

def addEventinfomenu(el):
	if el.value == "1":
		plugins.addPlugin(eventinfoDescriptor)
	elif el.value == "3":
		plugins.addPlugin(eventinfoDescriptor)
	else:
		try:
			plugins.removePlugin(eventinfoDescriptor)
		except ValueError as ve:
			print("[EPGRefresh] housekeepingExtensionsmenu got confused, tried to remove non-existant plugin entry... ignoring.")


config.plugins.epgrefresh_extra.show_autozap.addNotifier(AutozapExtensionsmenu, initial_call = False, immediate_feedback = True)
config.plugins.epgrefresh.show_in_extensionsmenu.addNotifier(housekeepingExtensionsmenu, initial_call = False, immediate_feedback = True)
config.plugins.epgrefresh.add_to_refresh.addNotifier(addEventinfomenu, initial_call = False, immediate_feedback = True)
extDescriptor = PluginDescriptor(name="EPGRefresh", description = _("Automatically refresh EPG"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc = extensionsmenu, needsRestart=False)
eventinfoDescriptor = PluginDescriptor(name= _("add to EPGRefresh"),description = _("add to EPGRefresh"), where = PluginDescriptor.WHERE_EVENTINFO, fnc = eventinfo, needsRestart=False)
autozapDescriptor = PluginDescriptor(name= _("Refresh-EPG / AutoZap"), description = _("AutoZap for refreshing EPG data"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc = autozap, needsRestart=False)

def Plugins(**kwargs):
	needsRestart = config.plugins.epgrefresh.enabled.value and not plugins.firstRun
	list = [
		PluginDescriptor(
			name = "EPGRefresh",
			where = [
				PluginDescriptor.WHERE_AUTOSTART,
				PluginDescriptor.WHERE_SESSIONSTART
			],
			fnc = autostart,
			wakeupfnc = getNextWakeup,
			needsRestart = needsRestart,
		),
		PluginDescriptor(
			where = PluginDescriptor.WHERE_SESSIONSTART,
			fnc = autostart_ChannelContextMenu,
			needsRestart = needsRestart,
		),
		PluginDescriptor(
			name = _("EPGRefresh"),
			description = _("Automatically refresh EPG"),
			where = PluginDescriptor.WHERE_PLUGINMENU, 
			fnc = main,
			icon = "plugin.png",
			needsRestart = needsRestart,
		),
		PluginDescriptor(
			name = "Manual EPG",
			description = _("manual save/load EPG"),
			where = PluginDescriptor.WHERE_MENU, 
			fnc = main_menu,
			needsRestart = needsRestart,
		),
		PluginDescriptor(
			name = "Manual EPG-refresh",
			where = PluginDescriptor.WHERE_MENU, 
			fnc = manualrefresh_menu,
			needsRestart = needsRestart,
		),
	]
	if config.plugins.epgrefresh.show_in_extensionsmenu.value:
		extDescriptor.needsRestart = needsRestart
		list.append(extDescriptor)
	profile = config.plugins.epgrefresh.add_to_refresh.value
	if profile == "1" or profile == "3": 
		eventinfoDescriptor.needsRestart = needsRestart
		list.append(eventinfoDescriptor)
	if config.plugins.epgrefresh_extra.show_autozap.value:
		autozapDescriptor.needsRestart = needsRestart
		list.append(autozapDescriptor)
	return list
