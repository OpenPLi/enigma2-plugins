# GUI (Screens)
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen

# GUI (Components)
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText

# Configuration
from Components.config import config

# for localized messages
from . import _


class EPGSearchSetup(Screen, ConfigListScreen):
	skin = """<screen name="EPGSearchSetup" position="center,center" size="585,420">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="config" position="5,50" size="575,250" scrollbarMode="showOnDemand" />
		<ePixmap pixmap="skin_default/div-h.png" position="0,325" zPosition="1" size="585,2" />
		<widget source="help" render="Label" position="5,329" size="575,85" font="Regular;21" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.title = _("EPGSearch Setup")
		ConfigListScreen.__init__(self, [], session=session, on_change=self.changedEntry)
		self.createSetup()

		self["config"].onSelectionChanged.append(self.updateHelp)

		# Initialize widgets
		self["key_green"] = StaticText(_("Save"))
		self["key_red"] = StaticText(_("Cancel"))
		self["help"] = StaticText()
		self.prev_add_search_to_epg = config.plugins.epgsearch.add_search_to_epg.value

		# Define Actions
		self["actions"] = ActionMap(["SetupActions"], {
			"cancel": self.keyCancel,
			"save": self.save
		}, -2)

	def createSetup(self):
		menu = []
		menu.append((_("Length of History"), config.plugins.epgsearch.history_length, _("How many entries to keep in the search history at most. 0 disables history entirely!")))
		menu.append((_("Add \"Search\" Button to EPG"), config.plugins.epgsearch.add_search_to_epg, _("If this setting is enabled, the plugin adds a \"Search\" Button to the regular EPG.")))
		menu.append((_("Type blue Button"), config.plugins.epgsearch.type_button_blue, _("Select type: 'Search and Select channel' or 'Search'.")))
		menu.append((_("Use event name for yellow button search"), config.plugins.epgsearch.yellow_eventname, _("Use the current event name as the initial search text. An empty search field is used otherwise.")))
		menu.append((_("Use Picons"), config.plugins.epgsearch.picons, _("If this setting is enabled, the plugin adds picons.")))
		menu.append((_("Search type"), config.plugins.epgsearch.search_type, _("Select type for search, \"partial match\" for the most extensive search, \"partial description\" for the most description search.")))
		menu.append((_("Search strictness"), config.plugins.epgsearch.search_case, _("Select whether or not you want to enforce case correctness.")))
		menu.append((_("Add \"Search event in EPG\" to event menu"), config.plugins.epgsearch.show_in_furtheroptionsmenu, _("Adds \"Search event in EPG\" item into the event menu (needs restart GUI)")))
		menu.append((_("Add \"Search event in EPG\" to channel menu"), config.plugins.epgsearch.search_in_channelmenu, _("Adds \"Search event in EPG\" item into the channel selection context menu (needs restart GUI)")))
		menu.append((_("Search only bouquets"), config.plugins.epgsearch.bouquet, _("If this setting is enabled, searching EPG in only services in user bouquets.")))
		if config.plugins.epgsearch.bouquet.value:
			menu.append((4 * " " + _("Exclude Last Scanned"), config.plugins.epgsearch.exclude_lastscanned, _("Exclude the Last Scanned bouquet when searching only in bouquets.")))
		menu.append((_("Include IPTV services"), config.plugins.epgsearch.include_iptv, _("Include IPTV services in search, in some cases slows down the searching.")))
		menu.append((_("Display name service as in bouquets"), config.plugins.epgsearch.favorit_name, _("If 'Search only bouquets' is enabled, show service name as in bouquets for renamed services.")))
		menu.append((_("Result filter"), config.plugins.epgsearch.filter_type, _("Use P+/- to filter result by short description or extended (only if short is missing). Partial: only items whose description is contained in selected event. Exact: only items with matching description. Full: identical whole description.")))
		self["config"].list = menu

	def changedEntry(self):
		current = self["config"].getCurrent()
		if current[1].isChanged():
			if current not in self.manipulatedItems:
				self.manipulatedItems.append(current)
		elif current in self.manipulatedItems:
			self.manipulatedItems.remove(current)
		self.createSetup()

	def updateHelp(self):
		cur = self["config"].getCurrent()
		if cur and len(cur) > 2:
			self["help"].text = cur[2]

	def save(self):
		self.keySave()
		current = config.plugins.epgsearch.add_search_to_epg.value
		if current and self.prev_add_search_to_epg != current:
			self.refreshPlugins()

	def refreshPlugins(self):
		from Components.PluginComponent import plugins
		from Tools.Directories import SCOPE_PLUGINS, resolveFilename
		plugins.clearPluginList()
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
