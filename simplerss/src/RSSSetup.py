# for localized messages
from . import _

from Screens.Screen import Screen
from Components.config import config, ConfigSubsection, ConfigYesNo, \
	ConfigText, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap
from Screens.MessageBox import MessageBox


class RSSFeedEdit(ConfigListScreen, Screen):
	"""Edit an RSS-Feed"""

	def __init__(self, session, id):
		Screen.__init__(self, session)
		self.skinName = ["RSSFeedEdit", "Setup"]

		s = config.plugins.simpleRSS.feed[id]
		list = [
			getConfigListEntry(_("Autoupdate"), s.autoupdate),
			getConfigListEntry(_("Feed URI"), s.uri)
		]

		ConfigListScreen.__init__(self, list, session)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))

		self["setupActions"] = ActionMap(["SetupActions"],
		{
			"save": self.save,
			"cancel": self.keyCancel
		}, -1)

		self.id = id
		self["VirtualKB"].setEnabled(True)
		self.onLayoutFinish.append(self.setCustomTitle)

	def setCustomTitle(self):
		self.setTitle(_("Simple RSS Reader Setup"))

	def save(self):
		config.plugins.simpleRSS.feed[self.id].save()
		config.plugins.simpleRSS.feed.save()
		self.close()

	def KeyText(self):
		if self["config"].getCurrent() is not None:
			if isinstance(self["config"].getCurrent()[1], ConfigText):
				ConfigListScreen.KeyText(self)

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()


class RSSSetup(ConfigListScreen, Screen):
	"""Setup for SimpleRSS, quick-edit for Feed-URIs and settings present."""
	skin = """
		<screen name="RSSSetup" position="center,center" size="560,400" title="Simple RSS Reader Setup" >
			<ePixmap position="0,0" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap position="140,0" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap position="280,0" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<ePixmap position="420,0" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="config" position="0,45" size="560,350" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, rssPoller=None):
		Screen.__init__(self, session)
		self.rssPoller = rssPoller
		self.list = []
		ConfigListScreen.__init__(self, self.list, session)
		self.createSetup()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("New"))
		self["key_blue"] = StaticText(_("Delete"))

		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"blue": self.delete,
			"yellow": self.new,
			"save": self.keySave,
			"cancel": self.keyCancel,
			"ok": self.ok
		}, -1)

		self.onLayoutFinish.append(self.setCustomTitle)
		self.onClose.append(self.abort)

	def setCustomTitle(self):
		self.setTitle(_("Simple RSS Reader Setup"))

	def createSetup(self):
		simpleRSS = config.plugins.simpleRSS

		# Create List of all Feeds
		list = [
			getConfigListEntry(_("Feed"), x.uri)
				for x in simpleRSS.feed
		]

		list.append(getConfigListEntry(_("Start automatically with Enigma2"), simpleRSS.autostart))

		# Save keep_running in instance as we want to dynamically add/remove it
		self.keep_running = getConfigListEntry(_("Keep running in background"), simpleRSS.keep_running)
		if not simpleRSS.autostart.value:
			list.append(self.keep_running)

		# Append Last two config Elements
		list.append(getConfigListEntry(_("Show new Messages as"), simpleRSS.update_notification))

		if simpleRSS.update_notification.value == "ticker":
			list.append(getConfigListEntry(_("Scroll speed (ms)"), simpleRSS.ticker_speed))

		list.extend((
			getConfigListEntry(_("Update Interval (min)"), simpleRSS.interval),
			getConfigListEntry(_("Fetch feeds from Google Reader?"), simpleRSS.enable_google_reader),
		))

		if simpleRSS.enable_google_reader.value:
			list.extend((
				getConfigListEntry(_("Google Username"), simpleRSS.google_username),
				getConfigListEntry(_("Google Password"), simpleRSS.google_password),
			))

		list.append(getConfigListEntry(_("Show in extensions menu"), simpleRSS.ext_menu))
		list.append(getConfigListEntry(_("--- Scanner automount ---"), simpleRSS.filescan))
		list.append(getConfigListEntry(_("< Create file any name.rss in USB device >"), simpleRSS.filescan))
		list.append(getConfigListEntry(_("< and write feeds link column >"), simpleRSS.filescan))
		self.list = list
		self["config"].setList(self.list)

	def notificationChanged(self, instance):
		import RSSTickerView as tv
		if instance and instance.value == "ticker":
			if tv.tickerView is None:
				print("[SimpleRSS] Ticker instantiated on startup")
				tv.tickerView = self.session.instantiateDialog(tv.RSSTickerView)
		else:
			if tv.tickerView is not None:
				self.session.deleteDialog(tv.tickerView)
				tv.tickerView = None

	def delete(self):
		cur = self["config"].getCurrent()
		if cur and cur[0] == _("Feed"):
			self.session.openWithCallback(
				self.deleteConfirm,
				MessageBox,
				_("Really delete this entry?\nIt cannot be recovered!")
			)

	def deleteConfirm(self, result):
		if result:
			id = self["config"].getCurrentIndex()
			del config.plugins.simpleRSS.feed[id]
			config.plugins.simpleRSS.feedcount.value -= 1

			self.createSetup()
			self["config"].setList(self.list)

	def ok(self):
		id = self["config"].getCurrentIndex()
		if id < len(config.plugins.simpleRSS.feed):
			self.session.openWithCallback(self.refresh, RSSFeedEdit, id)

	def refresh(self):
		# TODO: anything to be done here?
		pass

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def new(self):
		l = config.plugins.simpleRSS.feed
		s = ConfigSubsection()
		s.uri = ConfigText(default="http://", fixed_size=False)
		s.autoupdate = ConfigYesNo(default=True)
		id = len(l)
		l.append(s)

		self.session.openWithCallback(self.conditionalNew, RSSFeedEdit, id)

	def conditionalNew(self):
		id = len(config.plugins.simpleRSS.feed) - 1
		uri = config.plugins.simpleRSS.feed[id].uri

		# Check if new feed differs from default
		if uri.value == "http://":
			del config.plugins.simpleRSS.feed[id]
		else:
			config.plugins.simpleRSS.feedcount.value = id + 1
			self.createSetup()

	def keySave(self):
		# Tell Poller to recreate List if present
		if self.rssPoller is not None:
			self.rssPoller.triggerReload()
		ConfigListScreen.keySave(self)

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def abort(self):
		simpleRSS = config.plugins.simpleRSS

		# Handle ticker
		self.notificationChanged(simpleRSS.update_notification)

		# Keep feedcount sane
		simpleRSS.feedcount.value = len(simpleRSS.feed)
		simpleRSS.feedcount.save()


def addFeed(address, auto=False):
	l = config.plugins.simpleRSS.feed

	# Create new Item
	s = ConfigSubsection()
	s.uri = ConfigText(default="http://", fixed_size=False)
	s.autoupdate = ConfigYesNo(default=True)

	# Set values
	s.uri.value = address
	s.autoupdate.value = auto

	# Save
	l.append(s)
	l.save()
	config.plugins.simpleRSS.feedcount.value = len(config.plugins.simpleRSS.feed)
	config.plugins.simpleRSS.feedcount.save()
