from __future__ import print_function

from . import _, config

from twisted.internet import reactor

# GUI (Screens)
from Screens.MessageBox import MessageBox
from Tools.Notifications import AddPopup

# Standard EpgSelection and Multi-Epg
from Screens.ChoiceBox import ChoiceBox
from Screens.EpgSelection import EPGSelection
from Components.EpgList import EPGList, EPG_TYPE_SINGLE, EPG_TYPE_MULTI
from Components.ActionMap import ActionMap, HelpableActionMap
from Screens.TimeDateInput import TimeDateInput
from Screens.HelpMenu import HelpableScreen
from Components.config import config, ConfigClock
from Components.Sources.ServiceEvent import ServiceEvent
# ChannelContextMenu
from Screens.ChannelSelection import ChannelContextMenu, OFF, MODE_TV, service_types_tv
from Components.ChoiceList import ChoiceEntryComponent
from enigma import eServiceReference, iPlayableService, eServiceCenter, eEnv, eTimer
from Tools.BoundFunction import boundFunction
# Plugin
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
import os
from Logger import doLog

try:
	from Plugins.Extensions.SeriesPlugin.plugin import Plugins
	hasSeriesPlugin = True
except:
	hasSeriesPlugin = False

from AutoTimer import AutoTimer
autotimer = AutoTimer()
autopoller = None

AUTOTIMER_VERSION = "4.6.8"

try:
	from Plugins.SystemPlugins.MPHelp import registerHelp, XMLHelpReader
	from Tools.Directories import resolveFilename, SCOPE_PLUGINS
	reader = XMLHelpReader(resolveFilename(SCOPE_PLUGINS, "Extensions/AutoTimer/mphelp.xml"), translate=_)
	autotimerHelp = registerHelp(*reader)
except Exception as e:
	doLog("[AutoTimer] Unable to initialize MPHelp:", e, "- Help not available!")
	autotimerHelp = None


def isOriginalWebifInstalled():
	try:
		from Tools.Directories import fileExists
	except:
		return False
	pluginpath = eEnv.resolve('${libdir}/enigma2/python/Plugins/Extensions/WebInterface/plugin.py')
	if fileExists(pluginpath) or fileExists(pluginpath + "o") or fileExists(pluginpath + "c"):
		return True
	return False


def isOpenWebifInstalled():
	try:
		from Tools.Directories import fileExists
	except:
		return False
	pluginpath = eEnv.resolve('${libdir}/enigma2/python/Plugins/Extensions/OpenWebif/plugin.py')
	if fileExists(pluginpath) or fileExists(pluginpath + "o") or fileExists(pluginpath + "c"):
		return True
	return False

# Autostart


def autostart(reason, **kwargs):
	global autopoller

	# Startup
	if reason == 0 and config.plugins.autotimer.autopoll.value:
		# Start Poller
		if autopoller is None:
			from AutoPoller import AutoPoller
			autopoller = AutoPoller()
			autopoller.start()

			# Install NPB, main is too late because the Browser is already running
			import NotifiablePluginBrowser
			NotifiablePluginBrowser.install()
	# Shutdown
	elif reason == 1:
		# Stop Poller
		if autopoller is not None:
			autopoller.stop()
			autopoller = None

		# We re-read the config so we won't save wrong information
		try:
			autotimer.readXml()
		except Exception:
			# XXX: we should at least dump the error
			pass
		else:
			autotimer.writeXml()


def sessionstart(reason, **kwargs):
	if reason == 0 and "session" in kwargs:
		try:
			AutoTimerChannelContextMenuInit()
		except:
			pass
		try:
			AutoTimerEPGSelectionInit()
		except:
			pass
		if isOriginalWebifInstalled():
			try:
				from Plugins.Extensions.WebInterface.WebChilds.Toplevel import addExternalChild
				from Plugins.Extensions.WebInterface.WebChilds.Screenpage import ScreenPage
				from twisted.web import static
				from twisted.python import util
				from WebChilds.UploadResource import UploadResource

				from AutoTimerResource import AutoTimerDoParseResource, \
					AutoTimerListAutoTimerResource, AutoTimerAddOrEditAutoTimerResource, \
					AutoTimerRemoveAutoTimerResource, AutoTimerChangeSettingsResource, \
					AutoTimerSettingsResource, AutoTimerSimulateResource, AutoTimerTestResource, \
					AutoTimerUploadXMLConfigurationAutoTimerResource, AutoTimerAddXMLAutoTimerResource, API_VERSION
			except ImportError as ie:
				pass
			else:
				if hasattr(static.File, 'render_GET'):
					class File(static.File):
						def render_POST(self, request):
							return self.render_GET(request)
				else:
					File = static.File

				# webapi
				root = AutoTimerListAutoTimerResource()
				root.putChild('parse', AutoTimerDoParseResource())
				root.putChild('remove', AutoTimerRemoveAutoTimerResource())
				root.putChild('upload_xmlconfiguration', AutoTimerUploadXMLConfigurationAutoTimerResource())
				root.putChild('add_xmltimer', AutoTimerAddXMLAutoTimerResource())
				root.putChild('edit', AutoTimerAddOrEditAutoTimerResource())
				root.putChild('get', AutoTimerSettingsResource())
				root.putChild('set', AutoTimerChangeSettingsResource())
				root.putChild('simulate', AutoTimerSimulateResource())
				root.putChild('test', AutoTimerTestResource())
				addExternalChild(("autotimer", root, "AutoTimer-Plugin", API_VERSION, False))

				# webgui
				session = kwargs["session"]
				root = File(util.sibpath(__file__, "web-data"))
				root.putChild("web", ScreenPage(session, util.sibpath(__file__, "web"), True))
				root.putChild('tmp', File('/tmp'))
				root.putChild("uploadfile", UploadResource(session))
				addExternalChild(("autotimereditor", root, "AutoTimer", "1", True))
				doLog("[AutoTimer] Use WebInterface")
		else:
			if isOpenWebifInstalled():
				try:
					from Plugins.Extensions.WebInterface.WebChilds.Toplevel import addExternalChild
					from AutoTimerResource import AutoTimerDoParseResource, \
						AutoTimerListAutoTimerResource, AutoTimerAddOrEditAutoTimerResource, \
						AutoTimerRemoveAutoTimerResource, AutoTimerChangeSettingsResource, \
						AutoTimerSettingsResource, AutoTimerSimulateResource, AutoTimerTestResource, \
						AutoTimerUploadXMLConfigurationAutoTimerResource, AutoTimerAddXMLAutoTimerResource, API_VERSION
				except ImportError as ie:
					pass
				else:
					root = AutoTimerListAutoTimerResource()
					root.putChild('parse', AutoTimerDoParseResource())
					root.putChild('remove', AutoTimerRemoveAutoTimerResource())
					root.putChild('upload_xmlconfiguration', AutoTimerUploadXMLConfigurationAutoTimerResource())
					root.putChild('add_xmltimer', AutoTimerAddXMLAutoTimerResource())
					root.putChild('edit', AutoTimerAddOrEditAutoTimerResource())
					root.putChild('get', AutoTimerSettingsResource())
					root.putChild('set', AutoTimerChangeSettingsResource())
					root.putChild('simulate', AutoTimerSimulateResource())
					root.putChild('test', AutoTimerTestResource())
					addExternalChild(("autotimer", root, "AutoTimer-Plugin", API_VERSION))
					doLog("[AutoTimer] Use OpenWebif")


base_furtherOptions = None
baseEPGSelection__init__ = None
mepg_config_initialized = False


def AutoTimerEPGSelectionInit():
	global baseEPGSelection__init__, base_furtherOptions
	try:
		if baseEPGSelection__init__ is None:
			baseEPGSelection__init__ = EPGSelection.__init__
			EPGSelection.__init__ = AutoTimerEPGSelection__init__
			EPGSelection.menuCallbackAutoTimer = menuCallbackAutoTimer
			if base_furtherOptions is None:
				base_furtherOptions = EPGSelection.furtherOptions
			EPGSelection.furtherOptions = furtherOptions
	except:
		pass


def AutoTimerEPGSelection__init__(self, session, service, zapFunc=None, eventid=None, bouquetChangeCB=None, serviceChangeCB=None, parent=None):
	baseEPGSelection__init__(self, session, service, zapFunc, eventid, bouquetChangeCB, serviceChangeCB, parent)


def furtherOptions(self):
	if self.type == EPG_TYPE_SINGLE:
		if config.plugins.autotimer.add_to_epgselection.value:
			list = [
				(_("Add new AutoTimer"), "add"),
				(_("Preview for your AutoTimers"), "preview"),
				(_("Search new events matching for your AutoTimers"), "search"),
				(_("Open plugin"), "openplugin"),
				(_("Timers list"), "timerlist"),
			]
			dlg = self.session.openWithCallback(self.menuCallbackAutoTimer, ChoiceBox, title=_("Select action for AutoTimer:"), list=list)
			dlg.setTitle(_("Choice list AutoTimer"))
		else:
			base_furtherOptions(self)
	elif self.type == EPG_TYPE_MULTI:
		if config.plugins.autotimer.add_to_multiepgselection.value:
			list = [
				(_("Standard input date/time"), "input"),
				(_("Add new AutoTimer"), "add"),
				(_("Preview for your AutoTimers"), "preview"),
				(_("Search new events matching for your AutoTimers"), "search"),
				(_("Open plugin"), "openplugin"),
				(_("Timers list"), "timerlist"),
			]
			dlg = self.session.openWithCallback(self.menuCallbackAutoTimer, ChoiceBox, title=_("Select action for AutoTimer or input date/time:"), list=list)
			dlg.setTitle(_("Choice list AutoTimer"))
		else:
			base_furtherOptions(self)
	else:
		base_furtherOptions(self)


def menuCallbackAutoTimer(self, ret):
	ret = ret and ret[1]
	if ret:
		if ret == "add":
			from AutoTimerEditor import addAutotimerFromEvent
			cur = self["list"].getCurrent()
			evt = cur[0]
			sref = cur[1]
			if not evt:
				return
			try:
				addAutotimerFromEvent(self.session, evt=evt, service=sref)
			except:
				pass
		elif ret == "preview":
			from AutoTimerPreview import AutoTimerPreview
			try:
				total, new, modified, timers, conflicts, similars = autotimer.parseEPG(simulateOnly=True)
				self.session.open(AutoTimerPreview, timers)
			except:
				pass
		elif ret == "search":
			try:
				editCallback(self.session)
			except:
				pass
		elif ret == "timerlist":
			try:
				from Screens.TimerEdit import TimerEditList
				self.session.open(TimerEditList)
			except:
				pass
		elif ret == "openplugin":
			try:
				main(self.session)
			except:
				pass
		elif ret == "input":
			try:
				from time import time as my_time
				global mepg_config_initialized
				if not mepg_config_initialized:
					config.misc.prev_mepg_time = ConfigClock(default=my_time())
					mepg_config_initialized = True
				self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, config.misc.prev_mepg_time)
			except:
				pass


baseChannelContextMenu__init__ = None


def AutoTimerChannelContextMenuInit():
	try:
		global baseChannelContextMenu__init__
		if baseChannelContextMenu__init__ is None:
			baseChannelContextMenu__init__ = ChannelContextMenu.__init__
			ChannelContextMenu.__init__ = AutoTimerChannelContextMenu__init__
			ChannelContextMenu.addtoAutoTimer = addtoAutoTimer
	except:
		pass


def AutoTimerChannelContextMenu__init__(self, session, csel):
	baseChannelContextMenu__init__(self, session, csel)
	if csel.mode == MODE_TV:
		current = csel.getCurrentSelection()
		if current and current.valid():
			current_root = csel.getRoot()
			current_sel_path = current.getPath()
			current_sel_flags = current.flags
			inBouquetRootList = current_root and current_root.getPath().find('FROM BOUQUET "bouquets.') != -1 #FIXME HACK
			inBouquet = csel.getMutableList() is not None
			isPlayable = not (current_sel_flags & (eServiceReference.isMarker | eServiceReference.isDirectory))
			if config.plugins.autotimer.add_to_channelselection.value and csel.bouquet_mark_edit == OFF and not csel.movemode and isPlayable:
				callFunction = self.addtoAutoTimer
				self["menu"].list.insert(3, ChoiceEntryComponent(text=(_("create AutoTimer for current event"), boundFunction(callFunction, 1)), key="bullet"))


def addtoAutoTimer(self, add):
	sref = self.csel.servicelist.getCurrent()
	if not sref:
		return
	info = sref and eServiceCenter.getInstance().info(sref)
	event = info and info.getEvent(sref)
	if event is not None:
		sref = sref.toString()
		from AutoTimerEditor import addAutotimerFromEvent
		try:
			addAutotimerFromEvent(self.session, evt=event, service=sref)
		except:
			pass

# Mainfunction


def main(session, **kwargs):
	global autopoller

	try:
		autotimer.readXml()
	except SyntaxError as se:
		session.open(MessageBox, _("Your config file is not well-formed:\n%s") % (str(se)), type=MessageBox.TYPE_ERROR, timeout=10)
		return

	# Do not run in background while editing, this might screw things up
	if autopoller is not None:
		autopoller.pause()

	from AutoTimerOverview import AutoTimerOverview
	session.openWithCallback(
		editCallback,
		AutoTimerOverview,
		autotimer
	)


def handleAutoPoller():
	global autopoller

	# Start autopoller again if wanted
	if config.plugins.autotimer.autopoll.value:
		if autopoller is None:
			from AutoPoller import AutoPoller
			autopoller = AutoPoller()
		autopoller.start(initial=False)
	# Remove instance if not running in background
	else:
		autopoller = None


editTimer = eTimer()


def editCallback(session):
	# Don't parse EPG if editing was canceled
	if session is not None:
		if config.plugins.autotimer.always_write_config.value:
			autotimer.writeXml()
		delay = config.plugins.autotimer.editdelay.value
		editTimer.startLongTimer(int(delay))
	else:
		handleAutoPoller()


def parseEPGstart():
	if autotimer:
		autotimer.parseEPGAsync().addCallback(parseEPGCallback)#.addErrback(parseEPGErrback)


editTimer.callback.append(parseEPGstart)


def parseEPGCallback(ret):
	searchlog_txt = ""
	if config.plugins.autotimer.searchlog_write.value:
		logpath = config.plugins.autotimer.searchlog_path.value
		if logpath == "?likeATlog?":
			logpath = os.path.dirname(config.plugins.autotimer.log_file.value)
		path_search_log = os.path.join(logpath, "autotimer_search.log")
		if os.path.exists(path_search_log):
			searchlog_txt = open(path_search_log).read()
			#find last log in logfile
			if "\n########## " in searchlog_txt:
				searchlog_txt = searchlog_txt.split("\n########## ")
				searchlog_txt = str(searchlog_txt[-1]).split("\n")[2:]
				#check count and length of searchlog_entries
				maxlistcount = 10
				maxtextlength = 55
				listcount = len(searchlog_txt)
				searchlog_txt = searchlog_txt[:maxlistcount]
				for i, entry in enumerate(searchlog_txt):
					if len(entry) > maxtextlength:
						searchlog_txt[i] = entry[:maxtextlength - 3] + "..."
				searchlog_txt = "\n".join(searchlog_txt)
				if listcount > maxlistcount + 1:
					searchlog_txt += "\n" + "and %d searchlog-entries more ..." % (listcount - maxlistcount)

	AddPopup(
		_("Found a total of %d matching Events.\n%d Timer were added and\n%d modified,\n%d conflicts encountered,\n%d similars added.") % (ret[0], ret[1], ret[2], len(ret[4]), len(ret[5])) + "\n\n" + searchlog_txt,
		MessageBox.TYPE_INFO,
		config.plugins.autotimer.popup_timeout.value,
		'AT_PopUp_ID_ParseEPGCallback'
	)

	# Save xml
	if config.plugins.autotimer.always_write_config.value:
		autotimer.writeXml()
	handleAutoPoller()

# Movielist


def movielist(session, service, **kwargs):
	from AutoTimerEditor import addAutotimerFromService
	addAutotimerFromService(session, service)

# EPG Further Options


def epgfurther(session, selectedevent, **kwargs):
	from AutoTimerEditor import addAutotimerFromEvent
	try:
		addAutotimerFromEvent(session, selectedevent[0], selectedevent[1])
	except:
		pass

# Event Info and EventView Context Menu


def eventinfo(session, service=None, event=None, eventName="", **kwargs):
	if eventName != "":
		if service is not None and event is not None:
			try:
				from AutoTimerEditor import addAutotimerFromEvent, addAutotimerFromService
				if service.getPath() and service.getPath()[0] == "/":
					addAutotimerFromService(session, eServiceReference(str(service)))
				else:
					addAutotimerFromEvent(session, evt=event, service=service)
			except:
				pass
	else:
		from AutoTimerEditor import AutoTimerEPGSelection
		ref = session.nav.getCurrentlyPlayingServiceReference()
		if ref is not None:
			session.open(AutoTimerEPGSelection, ref)

# Extensions menu


def extensionsmenu(session, **kwargs):
	main(session, **kwargs)

# Extensions menu - only scan Autotimer


def extensionsmenu_scan(session, **kwargs):
	try:
		autotimer.readXml()
	except SyntaxError as se:
		session.open(MessageBox, _("Your config file is not well-formed:\n%s") % (str(se)), type=MessageBox.TYPE_ERROR, timeout=10)
		return
	editCallback(session)

# Movielist menu add to filterList


def add_to_filterList(session, service, services=None, *args, **kwargs):
	try:
		if services:
			if not isinstance(services, list):
				services = [services]
		else:
			services = [service]
		autotimer.addToFilterList(session, services)
	except Exception as e:
		print("[AutoTimer] Unable to add Recordtitle to FilterList:", e)
		doLog("[AutoTimer] Unable to add Recordtitle to FilterList:", e)


def housekeepingExtensionsmenu(el):
	if el.value:
		plugins.addPlugin(extDescriptor)
		plugins.addPlugin(extDescriptor_scan)
	else:
		try:
			plugins.removePlugin(extDescriptor)
			plugins.removePlugin(extDescriptor_scan)
		except ValueError as ve:
			doLog("[AutoTimer] housekeepingExtensionsmenu got confused, tried to remove non-existant plugin entry... ignoring.")


def timezoneChanged(self):
	if config.plugins.autotimer.autopoll.value and autopoller is not None:
		autopoller.pause()
		autopoller.start(initial=False)
		doLog("[AutoTimer] Timezone change detected.")


try:
	config.timezone.val.addNotifier(timezoneChanged, initial_call=False, immediate_feedback=False)
except AttributeError:
	doLog("[AutoTimer] Failed to load timezone notifier.")

config.plugins.autotimer.show_in_extensionsmenu.addNotifier(housekeepingExtensionsmenu, initial_call=False, immediate_feedback=True)
extDescriptor = PluginDescriptor(name=_("AutoTimer"), description=_("Edit Timers and scan for new Events"), where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=extensionsmenu, needsRestart=False)
extDescriptor_scan = PluginDescriptor(name=_("AutoTimer scan"), description=_("scan for new Events"), where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=extensionsmenu_scan, needsRestart=False)


def Plugins(**kwargs):
	l = [
		PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART, fnc=autostart, needsRestart=False),
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart, needsRestart=False),
		PluginDescriptor(name=_("AutoTimer"), description=_("Edit Timers and scan for new Events"), where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main, needsRestart=False),
		PluginDescriptor(name=_("Add AutoTimer"), description=_("add AutoTimer"), where=PluginDescriptor.WHERE_MOVIELIST, fnc=movielist, needsRestart=False),
		PluginDescriptor(name=_("add AutoTimer..."), where=PluginDescriptor.WHERE_EVENTINFO, fnc=eventinfo, needsRestart=False),
	]
	if hasSeriesPlugin:
		l.append(PluginDescriptor(name=_("add to AutoTimer filterList"), description=_("add to AutoTimer filterList"), where=PluginDescriptor.WHERE_MOVIELIST, fnc=add_to_filterList, needsRestart=False))
	if config.plugins.autotimer.show_in_furtheroptionsmenu.value:
		l.append(PluginDescriptor(name=_("Create AutoTimer"), where=PluginDescriptor.WHERE_EVENTINFO, fnc=epgfurther, needsRestart=False))
	if config.plugins.autotimer.show_in_extensionsmenu.value:
		l.append(extDescriptor)
		l.append(extDescriptor_scan)
	return l
