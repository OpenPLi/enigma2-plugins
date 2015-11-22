from __future__ import print_function

# for localized messages
from . import _

# GUI (Screens)
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Screens.ChoiceBox import ChoiceBox
from EPGRefreshChannelEditor import EPGRefreshServiceEditor

# GUI (Summary)
from Screens.Setup import SetupSummary

# GUI (Components)
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Button import Button
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

# Configuration
from Components.config import config, getConfigListEntry

from EPGRefresh import epgrefresh
from EPGSaveLoadConfiguration import EPGSaveLoadConfiguration
from Components.SystemInfo import SystemInfo
from enigma import getDesktop
from Screens.MessageBox import MessageBox


VERSION = "1.6"

weekdays = [
	_("Monday"),
	_("Tuesday"),
	_("Wednesday"),
	_("Thursday"),
	_("Friday"),
	_("Saturday"),
	_("Sunday"),
	]

HD = False
if getDesktop(0).size().width() >= 1280:
	HD = True
class EPGRefreshConfiguration(Screen, ConfigListScreen):
	"""Configuration of EPGRefresh"""
	if HD:
		skin = """<screen name="EPGRefreshConfiguration" position="center,center" size="680,630">
			<ePixmap position="20,5" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap position="180,5" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap position="320,5" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<ePixmap position="460,5" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
			<ePixmap position="642,15" size="35,25" pixmap="skin_default/buttons/key_info.png" alphatest="on" />

			<widget source="key_red" render="Label" position="20,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;18" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_green" render="Label" position="180,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;18" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_yellow" render="Label" position="320,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;18" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_blue" render="Label" position="460,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;18" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />

			<widget name="config" position="0,50" size="680,450" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,505" zPosition="1" size="680,2" />
			<widget source="help" render="Label" position="5,510" size="670,110" font="Regular;21" />
		</screen>"""
	else:
		skin = """<screen name="EPGRefreshConfiguration" position="center,center" size="600,430">
			<ePixmap position="0,5" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap position="140,5" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap position="280,5" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<ePixmap position="420,5" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
			<ePixmap position="562,15" size="35,25" pixmap="skin_default/buttons/key_info.png" alphatest="on" />

			<widget source="key_red" render="Label" position="0,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_green" render="Label" position="140,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_yellow" render="Label" position="280,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_blue" render="Label" position="420,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />

			<widget name="config" position="5,50" size="590,275" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,335" zPosition="1" size="565,2" />
			<widget source="help" render="Label" position="5,345" size="590,83" font="Regular;21" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		# Summary
		self.setup_title = _("EPGRefresh configuration")
		self.onChangedEntry = []

		# Although EPGRefresh keeps services in a Set we prefer a list
		self.services = (
			[x for x in epgrefresh.services[0]],
			[x for x in epgrefresh.services[1]]
		)

		self.list = [
			getConfigListEntry(_("Setup save / load EPG"), config.plugins.epgrefresh.setup_epg, _("Press the OK button to open the save / load EPG (+ configuration) menu.")),
			getConfigListEntry(_("Refresh EPG automatically"), config.plugins.epgrefresh.enabled, _("EPGRefresh needs to be explicitly started using the yellow button in this menu if this option is not enabled")),
			getConfigListEntry(_("Show in extensions menu"), config.plugins.epgrefresh.show_in_extensionsmenu, _("Enable this to show the EPGRefresh configuration menu in the extension menu.")),
			getConfigListEntry(_("Show \"add to EPGRefresh\" in"), config.plugins.epgrefresh.add_to_refresh, _("Select this item to add services to the EPGRefresh.")),
			getConfigListEntry(_("Show popup when refresh starts or ends"), config.plugins.epgrefresh.enablemessage, _("Enable this to show an informational message at the start and completion of the refresh.")),
			getConfigListEntry(_("Wake up from deep standby"), config.plugins.epgrefresh.wakeup, _("Enable this item to wake up the receiver from deep standby (if possible).")),
			getConfigListEntry(_("Choice days for refresh"), config.plugins.epgrefresh.day_profile, _("Select the days of the week for automatic refresh.")),
			getConfigListEntry(_("Timespan to remain on service (in seconds)"), config.plugins.epgrefresh.interval_seconds, _("This is the duration each service/channel will be tuned to during a refresh.")),
			getConfigListEntry(_("EPG refresh auto-start earliest (hh:mm)"), config.plugins.epgrefresh.begin, _("Automated refresh will start after this time of day, but before the time specified in next setting.")),
			getConfigListEntry(_("EPG refresh auto-start latest (hh:mm)"), config.plugins.epgrefresh.end, _("Automated refresh will start before this time of day, but after the time specified in previous setting.")),
			getConfigListEntry(_("Delay if not in standby (in minutes)"), config.plugins.epgrefresh.delay_standby, _("The duration that will be waited for the receiver to go into standby.")),
			getConfigListEntry(_("Force scan even if receiver is in use"), config.plugins.epgrefresh.force, _("Don't wait for the receiver to go into standby when starting a refresh cycle.")),
			getConfigListEntry(_("Shutdown after EPG refresh"), config.plugins.epgrefresh.afterevent, _("Whether the receiver should go into deep standby after refresh is completed.")),
			getConfigListEntry(_("Save EPG after refresh"), config.plugins.epgrefresh.save_epg, _("Save EPG in the cache file after refresh is completed.")),
			getConfigListEntry(_("Show 'EPGRefresh now' in main menu"), config.plugins.epgrefresh.start_on_mainmenu, _("If enabled, show 'EPGRefresh now' in main menu when currently no EPGRefresh is running.")),
			getConfigListEntry(_("Show 'Stop running EPGRefresh' in main menu"), config.plugins.epgrefresh.stop_on_mainmenu, _("If enabled, show 'Stop running EPGRefresh' in main menu when EPGPRefresh is running.")),
				]
		if SystemInfo.get("NumVideoDecoders", 1) > 1:
			self.list.insert(3, getConfigListEntry(_("Refresh EPG using"), config.plugins.epgrefresh.adapter, _("If you want to refresh the EPG in background, you can choose the method which best suits your needs here, e.g. hidden, fake recording or regular Picture in Picture.")))
		if config.ParentalControl.servicepinactive.value:
			self.list.append(getConfigListEntry(_("Skip protected Services"), config.plugins.epgrefresh.skipProtectedServices, _("Select mode the refresh for services/bouquets parental control.")))
		try:
			# try to import autotimer module to check for its existence
			from Plugins.Extensions.AutoTimer.AutoTimer import AutoTimer

			self.list.append(getConfigListEntry(_("Inherit Services from AutoTimer"), config.plugins.epgrefresh.inherit_autotimer, _("Extend the list of services to refresh by those your AutoTimers use?")))
			self.list.append(getConfigListEntry(_("Run AutoTimer after refresh"), config.plugins.epgrefresh.parse_autotimer, _("After a successful refresh the AutoTimer will automatically search for new matches if this is enabled.")))
			try:
				from Plugins.Extensions.SeriesPlugin.plugin import renameTimer
				self.list.append(getConfigListEntry(_("Timeout shutdown after refresh for SeriesPlugin (min)"), config.plugins.epgrefresh.timeout_shutdown,  _("If \"Run AutoTimer after refresh\" and \"Shutdown after EPG refresh\" enabled and use \"Label series\" for match, set long timeout."))) 
			except ImportError as ie:
				print("[EPGRefresh] SeriesPlugin Plugin not installed:", ie)
		except ImportError as ie:
			print("[EPGRefresh] AutoTimer Plugin not installed:", ie)

		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changed)

		def selectionChanged():
			if self["config"].current:
				self["config"].current[1].onDeselect(self.session)
			self["config"].current = self["config"].getCurrent()
			if self["config"].current:
				self["config"].current[1].onSelect(self.session)
			for x in self["config"].onSelectionChanged:
				x()

		self["config"].selectionChanged = selectionChanged
		self["config"].onSelectionChanged.append(self.updateHelp)

		# Initialize Buttons
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Refresh now"))
		self["key_blue"] = StaticText(_("Edit Services"))

		self["help"] = StaticText()

		# Define Actions
		self["actions"] = ActionMap(["SetupActions", "ColorActions", "ChannelSelectEPGActions", "HelpActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
				"yellow": self.forceRefresh,
				"blue": self.editServices,
				"showEPGList": self.keyInfo,
				"displayHelp": self.showHelp,
				"ok": self.keyOK,
			}
		)

		# Trigger change
		self.changed()
		self.onLayoutFinish.append(self.setCustomTitle)
		self.onFirstExecBegin.append(self.firstExec)

	def firstExec(self):
		from plugin import epgrefreshHelp
		if config.plugins.epgrefresh.show_help.value and epgrefreshHelp:
			config.plugins.epgrefresh.show_help.value = False
			config.plugins.epgrefresh.show_help.save()
			epgrefreshHelp.open(self.session)

	def setCustomTitle(self):
		self.setTitle(' '.join((_("EPGRefresh Configuration"), _("Version"), VERSION)))

	def showHelp(self):
		from plugin import epgrefreshHelp
		if epgrefreshHelp:
			epgrefreshHelp.open(self.session)

	def updateHelp(self):
		cur = self["config"].getCurrent()
		if cur:
			self["help"].text = cur[2]

	def forceRefresh(self):
		if config.plugins.epgrefresh.afterevent.value:
			choicelist = [
			(_("Return to TV viewing"), self.forceRefreshAfterNoShutdown),
			(_("Shutdown after EPG refresh"), self.forceRefreshStandart),
			]
			dlg = self.session.openWithCallback(self.menuCallback,ChoiceBox,list = choicelist,title= _("Select action after refresh:"))
			dlg.setTitle(_("Shutdown after EPG refresh enabled in setup..."))
		else:
			self.forceRefreshStandart()

	def menuCallback(self, ret = None):
		ret and ret[1]()

	def forceRefreshStandart(self):
		epgrefresh.services = (set(self.services[0]), set(self.services[1]))
		epgrefresh.forceRefresh(self.session)

	def forceRefreshAfterNoShutdown(self):
		epgrefresh.services = (set(self.services[0]), set(self.services[1]))
		epgrefresh.forceRefresh(self.session, dontshutdown = True)

	def keyOK(self):
		ConfigListScreen.keyOK(self)
		sel = self["config"].getCurrent()[1]
		if sel == config.plugins.epgrefresh.setup_epg:
			self.session.open(EPGSaveLoadConfiguration)
		if sel == config.plugins.epgrefresh.day_profile:
			self.session.open(EPGRefreshProfile)

	def editServices(self):
		self.session.openWithCallback(
			self.editServicesCallback,
			EPGRefreshServiceEditor,
			self.services
		)

	def editServicesCallback(self, ret):
		if ret:
			self.services = ret

	def changed(self):
		for x in self.onChangedEntry:
			try:
				x()
			except Exception:
				pass

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		return SetupSummary

	def cancelConfirm(self, result):
		if not result:
			return

		for x in self["config"].list:
			x[1].cancel()

		self.close(self.session)

	def keyInfo(self):
		lastscan = config.plugins.epgrefresh.lastscan.value
		if lastscan:
			from Tools.FuzzyDate import FuzzyTime
			scanDate = ', '.join(FuzzyTime(lastscan))
		else:
			scanDate = _("never")

		self.session.open(
				MessageBox,
				_("Last refresh was %s") % (scanDate,),
				type=MessageBox.TYPE_INFO
		)

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(
				self.cancelConfirm,
				MessageBox,
				_("Really close without saving settings?")
			)
		else:
			self.close(self.session)

	def keySave(self):
		epgrefresh.services = (set(self.services[0]), set(self.services[1]))
		epgrefresh.saveConfiguration()
		for x in self["config"].list:
			x[1].save()

		self.close(self.session)

class EPGRefreshProfile(ConfigListScreen,Screen):
	skin = """
			<screen position="center,center" size="400,230" title="EPGRefreshProfile" >
			<widget name="config" position="0,0" size="400,180" scrollbarMode="showOnDemand" />
			<widget name="key_red" position="0,190" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;18" transparent="1"/> 
			<widget name="key_green" position="140,190" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;18" transparent="1"/> 
			<ePixmap name="red"    position="0,190"   zPosition="2" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap name="green"  position="140,190" zPosition="2" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
		</screen>"""

	def __init__(self, session, args = 0):
		self.session = session
		Screen.__init__(self, session)

		self.list = []

		for i in range(7):
			self.list.append(getConfigListEntry(weekdays[i], config.plugins.epgrefresh_extra.day_refresh[i]))

		ConfigListScreen.__init__(self, self.list)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"green": self.save,
			"save": self.save,
			"cancel": self.cancel,
			"ok": self.save,
		}, -2)
		self.onLayoutFinish.append(self.setCustomTitle)

	def setCustomTitle(self):
		self.setTitle(_("Days Profile"))

	def save(self):
		day = False
		for i in range(0, 7):
			if config.plugins.epgrefresh_extra.day_refresh[i].value:
				for x in self["config"].list:
					x[1].save()
				day = True
				break
		if not day:
			self.session.open(MessageBox, _("You may not use this settings!\nAt least one day a week should be included!"), MessageBox.TYPE_INFO, timeout = 6)
			return
		self.close()


	def cancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()
