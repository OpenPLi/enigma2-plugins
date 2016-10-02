# for localized messages
from . import _

from Components.config import config, ConfigSubsection, ConfigSubList, ConfigNumber, ConfigText, ConfigSelection, ConfigYesNo, ConfigPassword, ConfigInteger, ConfigNothing
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Tools.BoundFunction import boundFunction
from RSSSetup import addFeed

# Initialize Configuration
config.plugins.simpleRSS = ConfigSubsection()
simpleRSS = config.plugins.simpleRSS
simpleRSS.update_notification = ConfigSelection(
	choices = [
		("notification", _("Notification")),
		("preview", _("Preview")),
		("ticker", _("Ticker")),
		("none", _("none"))
	],
	default = "preview"
)
simpleRSS.ticker_speed = ConfigInteger(default = 125, limits = (100, 900))
simpleRSS.interval = ConfigNumber(default=15)
simpleRSS.feedcount = ConfigNumber(default=0)
simpleRSS.autostart = ConfigYesNo(default=False)
simpleRSS.keep_running = ConfigYesNo(default=True)
simpleRSS.ext_menu = ConfigYesNo(default=True)
simpleRSS.filescan = ConfigNothing()
simpleRSS.feed = ConfigSubList()
i = 0
while i < simpleRSS.feedcount.value:
	s = ConfigSubsection()
	s.uri = ConfigText(default="http://", fixed_size=False)
	s.autoupdate =  ConfigYesNo(default=True)
	simpleRSS.feed.append(s)
	i += 1
	del s
simpleRSS.enable_google_reader = ConfigYesNo(default=False)
simpleRSS.google_username = ConfigText(default="", fixed_size=False)
simpleRSS.google_password = ConfigPassword(default="")

del simpleRSS, i

# Global Poller-Object
rssPoller = None

# Main Function
def main(session, **kwargs):
	# Get Global rssPoller-Object
	global rssPoller

	# Create one if we have none (no autostart)
	if rssPoller is None:
		from RSSPoller import RSSPoller
		rssPoller = RSSPoller()

	# Show Overview when we have feeds (or retrieving them from google)
	if rssPoller.feeds or config.plugins.simpleRSS.enable_google_reader.value:
		from RSSScreens import RSSOverview
		session.openWithCallback(closed, RSSOverview, rssPoller)
	# Show Setup otherwise
	else:
		from RSSSetup import RSSSetup
		session.openWithCallback(closed, RSSSetup, rssPoller)

# Plugin window has been closed
def closed():
	# If SimpleRSS should not run in Background: shutdown
	if not (config.plugins.simpleRSS.autostart.value or \
			config.plugins.simpleRSS.keep_running.value):

		# Get Global rssPoller-Object
		global rssPoller

		rssPoller.shutdown()
		rssPoller = None

# Autostart
def autostart(reason, **kwargs):
	global rssPoller

	if "session" in kwargs and config.plugins.simpleRSS.update_notification.value == "ticker":
		import RSSTickerView as tv
		if tv.tickerView is None:
			tv.tickerView = kwargs["session"].instantiateDialog(tv.RSSTickerView)

	# Instanciate when enigma2 is launching, autostart active and session present or installed during runtime
	if reason == 0 and config.plugins.simpleRSS.autostart.value and \
		(not plugins.firstRun or "session" in kwargs):

		from RSSPoller import RSSPoller
		rssPoller = RSSPoller()
	elif reason == 1:
		if rssPoller is not None:
			rssPoller.shutdown()
			rssPoller = None

def filescan_chosen(session, feed, item):
	if item and item[1] == "apply":
		for i in range(config.plugins.simpleRSS.feedcount.value):
			try:
				if config.plugins.simpleRSS.feed[i].uri.value in feed:
					for uri in feed:
						if uri == config.plugins.simpleRSS.feed[i].uri.value:
							feed.remove(uri)
			except:
				pass
		if feed:
			for uri in feed:
				addFeed(uri)
			session.open(MessageBox, _("%d feed(s) added to configuration.") % len(feed), type = MessageBox.TYPE_INFO, timeout = 5)
		else:
			session.open(MessageBox, _("Not found new feed(s)."), type = MessageBox.TYPE_INFO, timeout = 5)

# Filescan
def filescan_open(item, session, **kwargs):
	Len = len(item)
	if Len:
		file = item[0].path
		if file.endswith(".rss"):
			try:
				menu = [(_("Apply"), "apply"), (_("Close"), "close")]
				list = []
				f = open(file, "r")
				all_lines = f.readlines()
				for line in all_lines:
					if line.startswith(("http://", "https://")) and not line.endswith("#"):
						list.append(line)
				f.close()
				if list:
					session.openWithCallback(boundFunction(filescan_chosen, session, list), ChoiceBox, _("Found %d feed(s)") % len(list), menu)
			except:
				session.open(MessageBox, _("Read error %s") % file, type = MessageBox.TYPE_INFO, timeout = 5)
		else:
			# Add earch feed
			for each in item:
				addFeed(each)

			# Display Message
			session.open(MessageBox, _("%d Feed(s) were added to configuration.") % (Len), type = MessageBox.TYPE_INFO, timeout = 5)

from mimetypes import add_type
add_type("application/x-feed-rss", ".rss")

# Filescanner
def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath

	# Overwrite checkFile to detect remote files
	class RemoteScanner(Scanner):
		def checkFile(self, file):
			if file.path.endswith(".rss"):
				return True
			return file.path.startswith(("http://", "https://"))

	return [
		RemoteScanner(
			mimetypes = ("application/rss+xml", "application/atom+xml", "application/x-feed-rss"),
			paths_to_scan =
				(
					ScanPath(path = "", with_subdirs = False),
				),
			name = _("RSS-Reader"),
			description = _("Subscribe Newsfeed..."),
			openfnc = filescan_open,
		)
	]

def Plugins(**kwargs):
 	lst = [
		PluginDescriptor(
			name = _("RSS Reader"),
			description = _("A simple to use RSS reader"),
			where = PluginDescriptor.WHERE_PLUGINMENU,
			icon="rss.png",
			fnc=main,
			needsRestart=False,
		),
 		PluginDescriptor(
			where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART],
			fnc = autostart,
			needsRestart=False,
		),
 		PluginDescriptor(
			where = PluginDescriptor.WHERE_FILESCAN,
			fnc = filescan,
			needsRestart=False,
		)
	]
	if config.plugins.simpleRSS.ext_menu.value:
		lst.append(PluginDescriptor(name = _("View RSS..."), description = _("Let's you view current RSS entries"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main, needsRestart=False))
	return lst
