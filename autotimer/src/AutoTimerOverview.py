# for localized messages
from . import _, config

# GUI (Screens)
from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from AutoTimerEditor import AutoTimerEditor, AutoTimerChannelSelection
from AutoTimerImporter import AutoTimerImportSelector
from AutoTimerPreview import AutoTimerPreview
from AutoTimerSettings import AutoTimerSettings
from AutoTimerWizard import AutoTimerWizard

# for showSearchLog
import os
from time import localtime, strftime
from ShowLogScreen import ShowLogScreen

try:
	from Plugins.Extensions.SeriesPlugin.plugin import Plugins
except ImportError as ie:
	hasSeriesPlugin = False
else:
	hasSeriesPlugin = True

# GUI (Components)
from AutoTimerList import AutoTimerList
from Components.ActionMap import HelpableActionMap
from Components.Sources.StaticText import StaticText
from enigma import getDesktop


class AutoTimerOverviewSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="parent.Title" render="Label" position="6,4" size="120,21" font="Regular;18" />
		<widget source="entry" render="Label" position="6,25" size="120,21" font="Regular;16" />
		<widget source="global.CurrentTime" render="Label" position="56,46" size="82,18" font="Regular;16" >
			<convert type="ClockToText">WithSeconds</convert>
		</widget>
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["entry"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, text):
		self["entry"].text = text


HD = False
if getDesktop(0).size().width() >= 1280:
	HD = True


class AutoTimerOverview(Screen, HelpableScreen):
	"""Overview of AutoTimers"""
	if HD:
		skin = """<screen name="AutoTimerOverview" position="center,center" size="680,480" title="AutoTimer Overview">
				<ePixmap position="0,0" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
				<ePixmap position="160,0" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
				<ePixmap position="320,0" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
				<ePixmap position="480,0" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
				<ePixmap position="635,0" zPosition="1" size="35,25" pixmap="skin_default/buttons/key_menu.png" alphatest="on" />
				<ePixmap position="635,20" zPosition="1" size="35,25" pixmap="skin_default/buttons/key_info.png" alphatest="on" />
				<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;17" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget source="key_green" render="Label" position="160,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;17" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget source="key_yellow" render="Label" position="320,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;17" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget source="key_blue" render="Label" position="480,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;17" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget name="entries" position="5,45" size="650,425" scrollbarMode="showOnDemand" />
			</screen>"""
	else:
		skin = """<screen name="AutoTimerOverview" position="center,center" size="600,380" title="AutoTimer Overview">
				<ePixmap position="0,0" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
				<ePixmap position="140,0" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
				<ePixmap position="280,0" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
				<ePixmap position="420,0" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
				<ePixmap position="565,0" zPosition="1" size="35,25" pixmap="skin_default/buttons/key_menu.png" alphatest="on" />
				<ePixmap position="565,20" zPosition="1" size="35,25" pixmap="skin_default/buttons/key_info.png" alphatest="on" />
				<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget name="entries" position="5,45" size="590,325" scrollbarMode="showOnDemand" />
			</screen>"""

	def __init__(self, session, autotimer):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		# Save autotimer
		self.autotimer = autotimer

		self.changed = False

		# Button Labels
		self["key_red"] = StaticText(_("Timers list"))
		self["key_green"] = StaticText(_("Save and search now"))
		self["key_yellow"] = StaticText(_("Delete"))
		self["key_blue"] = StaticText(_("Add"))

		# Create List of Timers
		self["entries"] = AutoTimerList(autotimer.getSortedTupleTimerList())

		# Summary
		self.onChangedEntry = []
		self["entries"].onSelectionChanged.append(self.selectionChanged)

		# Define Actions
		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
				"ok": (self.ok, _("Edit selected AutoTimer")),
				"cancel": (self.cancel, _("Close and forget changes")),
			}
		)

		self["MenuActions"] = HelpableActionMap(self, "MenuActions",
			{
				"menu": (self.menu, _("Open Context Menu"))
			}
		)

		self["EPGSelectActions"] = HelpableActionMap(self, "EPGSelectActions",
			{
				"info": (self.showSearchLog, _("Show last SearchLog")),
			}
		)

		self["InfobarActions"] = HelpableActionMap(self, "InfobarActions",
			{
				"showTv": (self.showFilterTxt, _("Show AutoTimer FilterTxt")),
				"toggleTvRadio": (self.showFilterTxt, _("Show AutoTimer FilterTxt")),
			}
		)

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
				"red": (self.timer_menu, _("Open Timers list")),
				"green": (self.save, _("Close, save changes and search now")),
				"yellow": (self.remove, _("Remove selected AutoTimer")),
				"blue": (self.add, _("Add new AutoTimer")),
			}
		)

		self.onLayoutFinish.append(self.setCustomTitle)
		self.onFirstExecBegin.append(self.firstExec)

	def firstExec(self):
		from plugin import autotimerHelp
		if config.plugins.autotimer.show_help.value and autotimerHelp:
			config.plugins.autotimer.show_help.value = False
			config.plugins.autotimer.show_help.save()
			autotimerHelp.open(self.session)

	def setCustomTitle(self):
		from plugin import AUTOTIMER_VERSION
		self.setTitle(_("AutoTimer overview") + _(" - Version: ") + AUTOTIMER_VERSION)

	def createSummary(self):
		return AutoTimerOverviewSummary

	def selectionChanged(self):
		sel = self["entries"].getCurrent()
		text = sel and sel.name or ""
		for x in self.onChangedEntry:
			try:
				x(text)
			except Exception:
				pass

	def showSearchLog(self):
		if config.plugins.autotimer.searchlog_write.value:
			searchlog_txt = ""
			logpath = config.plugins.autotimer.searchlog_path.value
			if logpath == "?likeATlog?":
				logpath = os.path.dirname(config.plugins.autotimer.log_file.value)
			path_search_log = os.path.join(logpath, "autotimer_search.log")
			if os.path.exists(path_search_log):
				self.session.open(ShowLogScreen, path_search_log, _("searchLog"), "", "")
			else:
				self.session.open(MessageBox, _("No searchLog found!\n\nSo you have no new or modified timer at last autotimer-search."), MessageBox.TYPE_INFO)

	def showFilterTxt(self):
		if hasSeriesPlugin:
			from AutoTimerFilterList import AutoTimerFilterListOverview
			self.session.open(AutoTimerFilterListOverview)

	def timer_menu(self):
		from Screens.TimerEdit import TimerEditList
		self.session.open(TimerEditList)

	def add(self):
		newTimer = self.autotimer.defaultTimer.clone()
		newTimer.id = self.autotimer.getUniqueId()

		if config.plugins.autotimer.editor.value == "wizard":
			self.session.openWithCallback(
				self.addCallback,
				AutoTimerWizard,
				newTimer
			)
		elif config.plugins.autotimer.editor.value == "epg":
			self.session.openWithCallback(
				self.refresh,
				AutoTimerChannelSelection,
				self.autotimer
			)
		else:
			self.session.openWithCallback(
				self.addCallback,
				AutoTimerEditor,
				newTimer
			)

	def editCallback(self, ret):
		if ret:
			self.changed = True
			self.refresh()

	def addCallback(self, ret):
		if ret:
			self.changed = True
			self.autotimer.add(ret)
			self.refresh()

	def importCallback(self, ret):
		if ret:
			self.session.openWithCallback(
				self.addCallback,
				AutoTimerEditor,
				ret
			)

	def refresh(self, res=None):
		# Re-assign List
		cur = self["entries"].getCurrent()
		self["entries"].setList(self.autotimer.getSortedTupleTimerList())
		self["entries"].moveToEntry(cur)

	def ok(self):
		# Edit selected Timer
		current = self["entries"].getCurrent()
		if current is not None:
			self.session.openWithCallback(
				self.editCallback,
				AutoTimerEditor,
				current
			)

	def remove(self):
		# Remove selected Timer
		cur = self["entries"].getCurrent()
		if cur is not None:
			title = _("Message\nDo you really want to delete %s?") % (cur.name)
			list = ((_("Yes, and delete all timers generated by this autotimer"), "yes_delete"),
			(_("Yes, but keep timers generated by this autotimer"), "yes_keep"),
			(_("No"), "no"))
			self.session.openWithCallback(
				self.removeCallback,
				ChoiceBox,
				title=title,
				list=list,
				selection=0
			)

	def removeCallback(self, answer):
		cur = self["entries"].getCurrent()
		if answer:
			if (answer[1] != "no") and cur:
				self.changed = True
				self.autotimer.remove(cur.id)
				self.refresh()
				if (answer[1] == "yes_delete"):
					import NavigationInstance
					from RecordTimer import RecordTimerEntry
					recordHandler = NavigationInstance.instance.RecordTimer
					for timer in recordHandler.timer_list[:]:
						if timer and "autotimer" in timer.flags:
							remove = False
							for name in timer.flags:
								if name == cur.name:
									remove = True
							if timer.name == cur.name or remove:
								try:
									if not timer.isRunning():
										NavigationInstance.instance.RecordTimer.removeEntry(timer)
								except:
									pass
							#else:
							#	for entry in timer.log_entries:
							#		if len(entry) == 3:
							#			if entry[2] == '[AutoTimer] Try to add new timer based on AutoTimer '+cur.name+'.':
							#				try:
							#					if not timer.isRunning():
							#						NavigationInstance.instance.RecordTimer.removeEntry(timer)
							#				except:
							#					pass
							#				break

	def cancel(self):
		if self.changed:
			self.session.openWithCallback(self.cancelConfirm, ChoiceBox, title=_("Really close without saving settings?"), list=[(_("Close without saving"), "close"), (_("Close and save"), "close_save")])
		else:
			self.close(None)

	def cancelConfirm(self, ret):
		ret = ret and ret[1]
		if ret:
			self.autotimer.configMtime = -1
			if ret == 'close_save':
				self.autotimer.writeXml()
			self.close(None)

	def menu(self):
		list = [
			(_("Preview"), "preview"),
			(_("Import existing Timer"), "import"),
			(_("Import from EPG"), "import_epg"),
			(_("Edit new timer defaults"), "defaults"),
			(_("Clone selected timer"), "clone"),
			(_("Create a new timer using the classic editor"), "newplain"),
			(_("Create a new timer using the wizard"), "newwizard")
		]

		from plugin import autotimerHelp
		if autotimerHelp:
			list.append((_("Help"), "help"))
			list.append((_("Frequently asked questions"), "faq"))

		keys = ["menu"]
		keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "red", "green", "yellow", "blue"][:len(list)] + (len(list) - 14) * [""] + keys
		list.append((_("Setup"), "setup"))

		self.session.openWithCallback(
			self.menuCallback,
			ChoiceBox,
			title=_("AutoTimer Context Menu"),
			list=list,
			keys=keys
		)

	def menuCallback(self, ret):
		ret = ret and ret[1]
		if ret:
			if ret == "help":
				from plugin import autotimerHelp
				autotimerHelp.open(self.session)
			elif ret == "faq":
				from Plugins.SystemPlugins.MPHelp import PluginHelp, XMLHelpReader
				from Tools.Directories import resolveFilename, SCOPE_PLUGINS
				reader = XMLHelpReader(resolveFilename(SCOPE_PLUGINS, "Extensions/AutoTimer/faq.xml"), translate=_)
				autotimerFaq = PluginHelp(*reader)
				autotimerFaq.open(self.session)
			elif ret == "preview":
				total, new, modified, timers, conflicts, similars = self.autotimer.parseEPG(simulateOnly=True)
				self.session.open(
					AutoTimerPreview,
					timers
				)
			elif ret == "import":
				newTimer = self.autotimer.defaultTimer.clone()
				newTimer.id = self.autotimer.getUniqueId()

				self.session.openWithCallback(
					self.importCallback,
					AutoTimerImportSelector,
					newTimer
				)
			elif ret == "import_epg":
				self.session.openWithCallback(
					self.refresh,
					AutoTimerChannelSelection,
					self.autotimer
				)
			elif ret == "setup":
				self.session.open(
					AutoTimerSettings
				)
			elif ret == "defaults":
				self.session.open(
					AutoTimerEditor,
					self.autotimer.defaultTimer,
					editingDefaults=True
				)
			elif ret == "newwizard":
				newTimer = self.autotimer.defaultTimer.clone()
				newTimer.id = self.autotimer.getUniqueId()

				self.session.openWithCallback(
					self.addCallback, # XXX: we could also use importCallback... dunno what seems more natural
					AutoTimerWizard,
					newTimer
				)
			elif ret == "newplain":
				newTimer = self.autotimer.defaultTimer.clone()
				newTimer.id = self.autotimer.getUniqueId()

				self.session.openWithCallback(
					self.addCallback,
					AutoTimerEditor,
					newTimer
				)
			elif ret == "clone":
				current = self["entries"].getCurrent()
				if current is not None:
					newTimer = current.clone()
					newTimer.id = self.autotimer.getUniqueId()

					self.session.openWithCallback(
						self.addCallback,
						AutoTimerEditor,
						newTimer
					)

	def save(self):
		self.close(self.session)
