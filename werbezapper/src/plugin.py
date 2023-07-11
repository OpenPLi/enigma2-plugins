# for localized messages
from . import _
from Components.config import *
from Screens.ChannelSelection import ChannelContextMenu, OFF, MODE_TV, service_types_tv
from Components.ChoiceList import ChoiceEntryComponent
from enigma import eServiceReference, iPlayableService, eServiceCenter, eEPGCache, getDesktop
from time import time
from Tools.BoundFunction import boundFunction
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor

zapperInstance = None

WerbezapperInfoBarKeys = [
	["none", _("NONE"), ["KEY_RESERVED"]],
	["Green", _("GREEN"), ["KEY_GREEN"]],
	["Yellow", _("YELLOW"), ["KEY_YELLOW"]],
	["Radio", _("RADIO"), ["KEY_RADIO"]],
	["Text", _("TEXT"), ["KEY_TEXT"]],
	["Tv", _("TV"), ["KEY_TV"]],
	["Help", _("HELP"), ["KEY_HELP"]],
	["Timer", _("TIMER"), ["KEY_PROGRAM"]],
	["search", _("SEARCH"), ["KEY_SEARCH"]],
]

config.werbezapper = ConfigSubsection()
config.werbezapper.duration = ConfigNumber(default=5)
config.werbezapper.duration_not_event = ConfigInteger(default=60, limits=(10, 300))
config.werbezapper.standby = ConfigYesNo(default=False)
config.werbezapper.preserve_volume = ConfigYesNo(default=False)
config.werbezapper.channelselection_duration = ConfigNumber(default=1)
config.werbezapper.add_to_channelselection = ConfigYesNo(default=True)
config.werbezapper.channelselection_duration_stepsize = ConfigInteger(default=1, limits=(1, 20))
config.werbezapper.hotkey = ConfigSelection([(x[0], x[1]) for x in WerbezapperInfoBarKeys], "none")
config.werbezapper.monitoring_extmenu = ConfigYesNo(default=True)
config.werbezapper.icon_timer = ConfigYesNo(default=False)
config.werbezapper.icon_mode = ConfigSelection([("0", _("time")), ("1", _("service / time"))], "0")
config.werbezapper.x = ConfigInteger(default=60, limits=(0, 9999))
config.werbezapper.y = ConfigInteger(default=60, limits=(0, 9999))
config.werbezapper.z = ConfigSelection([(str(x), str(x)) for x in range(-20, 21)], "-1")

from .WerbeZapper import WerbeZapper, WerbezapperSettings
sz_w = getDesktop(0).size().width()


def main(session=None, servicelist=None, **kwargs):
	if servicelist is None:
		from Screens.InfoBar import InfoBar
		servicelist = InfoBar.instance and InfoBar.instance.servicelist
	if session and servicelist:
		global zapperInstance
		if zapperInstance is None:
			zapperInstance = session.instantiateDialog(WerbeZapper, servicelist, cleanup)
		zapperInstance.showSelection()


def startstop(session=None, servicelist=None, **kwargs):
	if servicelist is None:
		from Screens.InfoBar import InfoBar
		servicelist = InfoBar.instance and InfoBar.instance.servicelist
	if session and servicelist:
		global zapperInstance
		if zapperInstance is None:
			zapperInstance = session.instantiateDialog(WerbeZapper, servicelist, cleanup)
		if not zapperInstance.monitor_timer.isActive():
			zapperInstance.startMonitoring()
		else:
			zapperInstance.stopMonitoring()


def cleanup():
	global zapperInstance
	if zapperInstance is not None:
		zapperInstance.shutdown()
		zapperInstance.doClose()
		zapperInstance = None


class WerbeZapperSilder(ConfigListScreen, Screen):
	if sz_w < 1920:
		skin = """<screen name="WerbeZapperSilder" position="center,center" size="600,200" title="Add Zap Timer" backgroundColor="#31000000" flags="wfNoBorder" >
			<widget source="header" render="Label" position="0,0" zPosition="1" size="600,78" halign="center" valign="center" noWrap="1" font="Regular;22" foregroundColor="yellow" backgroundColor="background" shadowColor="black" shadowOffset="-2,-2" transparent="1"/>
			<widget name="config" position="25,80" size="550,25" scrollbarMode="showOnDemand" zPosition="1" foregroundColor="white" backgroundColor="background" />
			<widget source="time" render="Label" position="0,125" zPosition="1" size="600,75" noWrap="1" halign="center" font="Regular;20" foregroundColor="#00E0E0D0" backgroundColor="background" shadowColor="black" shadowOffset="-2,-2" transparent="1"/>
		</screen>"""
	else:
		skin = """<screen name="WerbeZapperSilder" position="center,center" size="680,250" title="Add Zap Timer" backgroundColor="#31000000" flags="wfNoBorder" >
			<widget source="header" render="Label" position="0,0" zPosition="1" size="680,98" halign="center" valign="center" noWrap="1" font="Regular;26" foregroundColor="yellow" backgroundColor="background" shadowColor="black" shadowOffset="-2,-2" transparent="1"/>
			<widget name="config" position="40,100" size="600,25" scrollbarMode="showOnDemand" zPosition="1" foregroundColor="white" backgroundColor="background" />
			<widget source="time" render="Label" position="0,155" zPosition="1" size="680,95" noWrap="1" halign="center" font="Regular;26" foregroundColor="#00E0E0D0" backgroundColor="background" shadowColor="black" shadowOffset="-2,-2" transparent="1"/>
		</screen>"""


	def __init__(self, session, servicelist=None, remaining=0):
		self.servicelist = servicelist
		self.remaining = remaining
		Screen.__init__(self, session)
		self["time"] = StaticText()
		if self.remaining > 0 and self.remaining < 300:
			self["time"].setText(_("Button Info/EPG\nSet time begin next event: %d min") % (self.remaining))
		self["header"] = StaticText("")
		self["setupActions"] = ActionMap(["SetupActions", "ChannelSelectEPGActions"],
			{
				"ok": self.keyOk,
				"showEPGList": self.setSliderTime,
				"cancel": self.cancel,
			}, -2)
		self.initConfig()
		ConfigListScreen.__init__(self, [])
		self.createSetup()

	def keyOk(self):
		global zapperInstance
		if zapperInstance is None:
			zapperInstance = self.session.instantiateDialog(WerbeZapper, self.servicelist, cleanup)
		if self.servicelist:
			zap = int(self.duration.value)
			zapperInstance.addStartTimer(duration=zap)
		self.close()

	def initConfig(self):
		self.duration = ConfigSlider(default=config.werbezapper.channelselection_duration.value, increment=config.werbezapper.channelselection_duration_stepsize.value, limits=(1, 300))
		self.duration.addNotifier(self.timeSettingChanged)

	def createSetup(self):
		list = []
		list.append(getConfigListEntry(_("Set zap time"), self.duration))
		self["config"].list = list
		self["config"].l.setList(list)

	def setSliderTime(self):
		if self.remaining > 0 and self.remaining < 300:
			try:
				cur = self["config"].getCurrent()
				slider = cur[1]
				slider.value = self.remaining
				self["config"].instance.invalidate()
			except:
				pass

	def cancel(self):
		self.close()

	def timeSettingChanged(self, elem):
		self.updateHeaderText()

	def updateHeaderText(self):
		if "header" in self:
			self["header"].setText(_("%d min") % (self.duration.value))


from keyids import KEYIDS
from enigma import eActionMap


class WerbezapperInfoBar:
	def __init__(self, session, infobar):
		self.session = session
		self.infobar = infobar
		self.lastKey = None
		self.hotkeys = {}
		for x in WerbezapperInfoBarKeys:
			self.hotkeys[x[0]] = [KEYIDS[key] for key in x[2]]
		eActionMap.getInstance().bindAction('', -10, self.keyPressed)

	def keyPressed(self, key, flag):
		for k in self.hotkeys[config.werbezapper.hotkey.value]:
			if key == k and self.session.current_dialog == self.infobar:
				if flag == 0:
					self.lastKey = key
				elif self.lastKey != key or flag == 4:
					self.lastKey = None
					continue
				elif flag == 3:
					self.lastKey = None
					self.showSetup()
				elif flag == 1:
					self.lastKey = None
					global zapperInstance
					if zapperInstance is None:
						from Screens.InfoBar import InfoBar
						InfoBarInstance = InfoBar.instance
						if InfoBarInstance is not None:
							servicelist = InfoBarInstance.servicelist
							zapperInstance = self.session.instantiateDialog(WerbeZapper, servicelist, cleanup)
					if zapperInstance:
						zapperInstance.showSelection()
				return 1
		return 0

	def showSetup(self):
		self.session.open(WerbezapperSettings)


baseInfoBar__init__ = None


def zapInfoBar__init__(self, session):
	baseInfoBar__init__(self, session)
	self.werbezapperinfobar = WerbezapperInfoBar(session, self)


def session_start(reason, **kwargs):
	if reason == 0 and "session" in kwargs:
		pass
		#global baseInfoBar__init__
		#try:
		#	from Screens.InfoBar import InfoBar
		#	if baseInfoBar__init__ is None:
		#		baseInfoBar__init__ = InfoBar.__init__
		#	InfoBar.__init__ = zapInfoBar__init__
		#except:
		#	pass


def start_channelselection(session=None, service=None):
	from Screens.InfoBar import InfoBar
	servicelist = InfoBar.instance and InfoBar.instance.servicelist
	if service and session and servicelist:
		epg = eEPGCache.getInstance()
		try:
			event = epg.lookupEventTime(service, -1, 0)
		except:
			event = None
		if event:
			now = int(time())
			start = event.getBeginTime()
			duration = event.getDuration()
			end = start + duration
			remaining_event = (end - now) / 60
		else:
			remaining_event = 0
		session.open(WerbeZapperSilder, servicelist, remaining=remaining_event)


def Plugins(**kwargs):
	l = [
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=session_start, needsRestart=False),
		PluginDescriptor(name=_("Werbezapper"), description=_("Automatically zaps back to current service after given Time"), where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main, needsRestart=False),
	]
	if config.werbezapper.monitoring_extmenu.value:
		l.append(PluginDescriptor(name=_("Werbezapper Start / Stop monitoring"), description=_("Start / Stop monitoring instantly"), where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=startstop, needsRestart=False))
	if config.werbezapper.add_to_channelselection.value:
		l.append(PluginDescriptor(name=_("add zap timer for service"), where=PluginDescriptor.WHERE_CHANNEL_CONTEXT_MENU, fnc=start_channelselection, needsRestart=False))
	return l
