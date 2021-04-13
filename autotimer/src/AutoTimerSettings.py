# for localized messages
from . import _

# GUI (Screens)
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen

# GUI (Summary)
from Screens.Setup import SetupSummary

# GUI (Components)
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from enigma import getDesktop
# Configuration
from Components.config import config, getConfigListEntry

from Components.Sources.Boolean import Boolean
from Components.Pixmap import Pixmap

HD = False
if getDesktop(0).size().width() >= 1280:
	HD = True


class AutoTimerSettings(Screen, ConfigListScreen):
	if HD:
		skin = """<screen name="AutoTimerSettings" title="AutoTimer Settings" position="center,center" size="750,635">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="5,50" size="740,475" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,530" zPosition="1" size="750,2" />
			<widget source="help" render="Label" position="5,535" size="740,110" font="Regular;21" />
			<widget source="VKeyIcon" render="Pixmap" pixmap="skin_default/buttons/key_text.png" position="5,597" zPosition="10" size="52,38" transparent="1" alphatest="on">
				<convert type="ConditionalShowHide"/>
			</widget>
		</screen>"""
	else:
		skin = """<screen name="AutoTimerSettings" title="AutoTimer Settings" position="center,center" size="565,430">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="5,50" size="555,300" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,355" zPosition="1" size="565,2" />
			<widget source="help" render="Label" position="5,360" size="555,70" font="Regular;20" />
			<widget source="VKeyIcon" render="Pixmap" pixmap="skin_default/buttons/key_text.png" position="5,405" zPosition="10" size="35,25" transparent="1" alphatest="on">
				<convert type="ConditionalShowHide"/>
			</widget>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		# Summary
		self.setup_title = _("AutoTimer Settings")
		self.onChangedEntry = []

		self.list = [
			getConfigListEntry(_("Poll automatically"), config.plugins.autotimer.autopoll, _("Unless this is enabled AutoTimer will NOT automatically look for events matching your AutoTimers but only when you leave the GUI with the green button.")),
			getConfigListEntry(_("Startup delay (in min)"), config.plugins.autotimer.delay, _("This is the delay in minutes that the AutoTimer will wait on initial launch to not delay enigma2 startup time.")),
			getConfigListEntry(_("Delay after editing (in sec)"), config.plugins.autotimer.editdelay, _("This is the delay in seconds that the AutoTimer will wait after editing the AutoTimers.")),
			getConfigListEntry(_("Poll Interval (in h)"), config.plugins.autotimer.interval, _("This is the delay in hours that the AutoTimer will wait after a search to search the EPG again.")),
			getConfigListEntry(_("Timeout (in min)"), config.plugins.autotimer.timeout, _("This is the duration in minutes that the AutoTimer is allowed to run.")),
			getConfigListEntry(_("Max. match search events"), config.plugins.autotimer.max_search_events_match, _("If your receiver has a small amount of memory, use mode 'Standard (1000 events)' or 'Advanced (2000 events)'.")),
			getConfigListEntry(_("Clear memory before auto run"), config.plugins.autotimer.clear_memory, _("If your receiver has a small amount of memory, clear memory before poll AutoTimer run.")),
			getConfigListEntry(_("Only add timer for next x days"), config.plugins.autotimer.maxdaysinfuture, _("You can control for how many days in the future timers are added. Set this to 0 to disable this feature.")),
			getConfigListEntry(_("Allow double timer for different services"), config.plugins.autotimer.enable_multiple_timer, _("Here you can specify whether simultaneous timers of the same program can be created. This allows simultaneous recording of a program with different resolutions. (e.g. SD service and HD service).")),
			getConfigListEntry(_("Show in extension menu"), config.plugins.autotimer.show_in_extensionsmenu, _("Enable this to be able to access the AutoTimer Overview from within the extension menu.")),
			getConfigListEntry(_("Show in event menu"), config.plugins.autotimer.show_in_furtheroptionsmenu, _("Enable this to add item for create the AutoTimer into event menu (needs restart GUI).")),
			getConfigListEntry(_("Show \"add to AutoTimer\" in channel selection menu"), config.plugins.autotimer.add_to_channelselection, _("Enable this to be able to access the add to AutoTimer from the channel selection context menu.")),
			getConfigListEntry(_("Add \"Choice list AutoTimer\" menu button to single-EPG"), config.plugins.autotimer.add_to_epgselection, _("If this is enabled, up on the Menu button in the standard single-EPG will list of choices for AutoTimer.")),
			getConfigListEntry(_("Add \"Choice list AutoTimer\" menu button to multi-EPG"), config.plugins.autotimer.add_to_multiepgselection, _("If this is enabled, up on the MENU button in the multi-EPG will list of choices for AutoTimer.")),
			#getConfigListEntry(_("Add \"Choice list AutoTimer\" menu button to GraphMultiEpg"), config.plugins.autotimer.add_to_graph, _("If this is enabled, up on the MENU button in the GraphMultiEpg will list of choices for AutoTimer.")),
			getConfigListEntry(_("Modify existing timers"), config.plugins.autotimer.refresh, _("This setting controls the behavior when a timer matches a found event.")),
			getConfigListEntry(_("Guess existing timer based on begin/end"), config.plugins.autotimer.try_guessing, _("If this is enabled an existing timer will also be considered recording an event if it records at least 80% of the it.")),
			getConfigListEntry(_("Add similar timer on conflict"), config.plugins.autotimer.addsimilar_on_conflict, _("If a timer conflict occurs, AutoTimer will search outside the timespan for a similar event and add it.")),
			getConfigListEntry(_("Add timer as disabled on conflict"), config.plugins.autotimer.disabled_on_conflict, _("This toggles the behavior on timer conflicts. If an AutoTimer matches an event that conflicts with an existing timer it will not ignore this event but add it disabled.")),
			getConfigListEntry(_("Include \"AutoTimer\" in tags"), config.plugins.autotimer.add_autotimer_to_tags, _("If this is selected, the tag \"AutoTimer\" will be given to timers created by this plugin.")),
			getConfigListEntry(_("Include AutoTimer name in tags"), config.plugins.autotimer.add_name_to_tags, _("If this is selected, the name of the respective AutoTimer will be added as a tag to timers created by this plugin.")),
			getConfigListEntry(_("Show notification on conflicts"), config.plugins.autotimer.notifconflict, _("By enabling this you will be notified about timer conflicts found during automated polling. There is no intelligence involved, so it might bother you about the same conflict over and over.")),
			getConfigListEntry(_("Show notification on similars"), config.plugins.autotimer.notifsimilar, _("By enabling this you will be notified about similar timers added during automated polling. There is no intelligence involved, so it might bother you about the same conflict over and over.")),
			getConfigListEntry(_("Show notification on added timers"), config.plugins.autotimer.notiftimers, _("By enabling this you will be notified about timer(s) added during automated polling. Just not in standby mode.")),
			getConfigListEntry(_("Editor for new AutoTimers"), config.plugins.autotimer.editor, _("The editor to be used for new AutoTimers. This can either be the Wizard or the classic editor.")),
			getConfigListEntry(_("Support \"Fast Scan\"?"), config.plugins.autotimer.fastscan, _("When supporting \"Fast Scan\" the service type is ignored. You don't need to enable this unless your Image supports \"Fast Scan\" and you are using it.")),
			getConfigListEntry(_("Skip poll during records"), config.plugins.autotimer.skip_during_records, _("If enabled, the polling will be skipped if a recording is in progress.")),
			getConfigListEntry(_("Only poll while in standby"), config.plugins.autotimer.onlyinstandby, _("When this is enabled AutoTimer will ONLY check for new events whilst in stanadby.")),
			getConfigListEntry(_("Style auto timers list"), config.plugins.autotimer.style_autotimerslist, _("If the style is advanced, you will see more information about each auto timer. This change will not take effect until the plugin has started again.")),
			getConfigListEntry(_("Skip poll during epg refresh"), config.plugins.autotimer.skip_during_epgrefresh, _("If enabled, the polling will be skipped if EPGRefresh is currently running.")),
			getConfigListEntry(_("Popup timeout in seconds"), config.plugins.autotimer.popup_timeout, _("If 0, the popup will remain open.")),
			getConfigListEntry(_("Remove not existing events"), config.plugins.autotimer.check_eit_and_remove, _("Check the event id (eit) and remove the timer if there is no corresponding EPG event. Due to compatibility issues with SerienRecorder and IPRec, only timer created by AutoTimer are affected.")),
			getConfigListEntry(_("Reload timers list after search events"), config.plugins.autotimer.remove_double_and_conflicts_timers, _("If this enabled, will check the list of timers, conflicting autotimers are disabled, the duplicate autotimers will be deleted.")),
			getConfigListEntry(_("Always write config"), config.plugins.autotimer.always_write_config, _("Write the config file after every change which the user quits by saving.")),
			getConfigListEntry(_("Create debug log file"), config.plugins.autotimer.log_write, _("If this enabled, debug Autotimer write in log file.")),
			getConfigListEntry(_("Path debug log"), config.plugins.autotimer.log_file, _("Specify the name and location for the log.")),
			getConfigListEntry(_("Print shell log"), config.plugins.autotimer.log_shell, _("If this enabled, debug log print in console mode start enigma2.")),
			getConfigListEntry(_("Create searchlog file"), config.plugins.autotimer.searchlog_write, _("If this enabled, search log write in autotimer_search.log.")),
			getConfigListEntry(_("Select the path for autotimer_search.log"), config.plugins.autotimer.searchlog_path, _("Select the path where the autotimer_search.log should be saved")),
			getConfigListEntry(_("Max. count for saved searchlog"), config.plugins.autotimer.searchlog_max, _("Select the count of the last saved searchlogs (min=5 max=20)")),
			]
		try:
			from Plugins.Extensions.SeriesPlugin.plugin import getSeasonEpisode4
			self.list.append(getConfigListEntry(_("Save/check labeled series in filterlist (SeriesPlugin)"), config.plugins.autotimer.series_save_filter, _("Save the by SeriesPlugin generated timer-name in a filterlist to filter at later timer-searches (only with SeriesPlugin)")))
		except:
			pass

		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changed)

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

		# Initialize widgets
		self["key_green"] = StaticText(_("OK"))
		self["key_red"] = StaticText(_("Cancel"))
		self["help"] = StaticText()

		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		# Define Actions
		self["actions"] = ActionMap(["SetupActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
			}
		)

		# Trigger change
		self.changed()

		self.onLayoutFinish.append(self.setCustomTitle)

	def setCustomTitle(self):
		from plugin import AUTOTIMER_VERSION
		self.setTitle(_("Configure AutoTimer behavior") + _(" - Version: ") + AUTOTIMER_VERSION)

	def updateHelp(self):
		cur = self["config"].getCurrent()
		if cur:
			self["help"].text = cur[2]

	def changed(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		return SetupSummary
