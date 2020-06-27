# -*- coding: UTF-8 -*-
from . import _
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigSet, ConfigInteger, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Sources.List import List
from Screens.ChannelSelection import ChannelSelection
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen
from enigma import eServiceCenter

################################################

config.plugins.ZapHistoryConfigurator = ConfigSubsection()
config.plugins.ZapHistoryConfigurator.enable_zap_history = ConfigSelection(choices = {"off": _("disabled"), "on": _("enabled"), "parental_lock": _("disabled at parental lock")}, default="on")
config.plugins.ZapHistoryConfigurator.maxEntries_zap_history = ConfigInteger(default=20, limits=(1, 60))
config.plugins.ZapHistoryConfigurator.history_tv = ConfigSet(choices = [])
config.plugins.ZapHistoryConfigurator.history_radio = ConfigSet(choices = [])

################################################

def addToHistory(instance, ref):
	if config.plugins.ZapHistoryConfigurator.enable_zap_history.value == "off":
		return
	if config.ParentalControl.servicepinactive.value and config.plugins.ZapHistoryConfigurator.enable_zap_history.value == "parental_lock":
		if parentalControl.getProtectionLevel(ref.toCompareString()) != -1:
			return
	if instance.servicePath is not None:
		tmp = instance.servicePath[:]
		tmp.append(ref)
		try: del instance.history[instance.history_pos+1:]
		except Exception, e: pass
		instance.history.append(tmp)
		hlen = len(instance.history)
		if hlen > config.plugins.ZapHistoryConfigurator.maxEntries_zap_history.value:
			del instance.history[0]
			hlen -= 1
		instance.history_pos = hlen-1

ChannelSelection.addToHistory = addToHistory

################################################

class ZapHistoryConfigurator(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="560,90">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" transparent="1" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" transparent="1" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" transparent="1" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" transparent="1" alphatest="on"/>
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1"/>
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1"/>
		<widget name="config" position="0,40" size="560,50" scrollbarMode="showOnDemand"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.setTitle(_("Zap-History Configurator"))

		ConfigListScreen.__init__(self, [
			getConfigListEntry(_("Enable zap history:"), config.plugins.ZapHistoryConfigurator.enable_zap_history),
			getConfigListEntry(_("Maximum zap history entries:"), config.plugins.ZapHistoryConfigurator.maxEntries_zap_history)])
		
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
			{
				"ok": self.save,
				"green": self.save,
				"cancel": self.exit,
				"red": self.exit
			}, -2)
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))

	def save(self):
		for x in self["config"].list:
			x[1].save()
		self.close()

	def exit(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

################################################

class ZapHistoryBrowser(Screen, ProtectedScreen):
	skin = """
	<screen name="ZapHistoryBrowser" position="center,center" size="560,440">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" transparent="1" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" transparent="1" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" transparent="1" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" transparent="1" alphatest="on"/>
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1"/>
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1"/>
		<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1"/>
		<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1"/>
		<widget source="list" render="Listbox" position="0,40" size="560,400" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent" >
			{
				"template":[
						MultiContentEntryText(pos=(2,2), size=(556,23), font=0, flags=RT_HALIGN_LEFT, text=0),
						MultiContentEntryText(pos=(2,26), size=(556,21), font=1, flags=RT_HALIGN_LEFT, text=1),
				],
				"fonts": [gFont("Regular",20), gFont("Regular",18)],
				"itemHeight": 50
			}
			</convert>
		</widget>
	</screen>"""

	def __init__(self, session, servicelist):
		Screen.__init__(self, session)
		ProtectedScreen.__init__(self)
		self.session = session

		self.servicelist = servicelist
		self.serviceHandler = eServiceCenter.getInstance()
		self.allowChanges = True

		self.setTitle(_("Zap-History Browser"))

		self.list = []
		self["list"] = List(self.list)

		self["key_red"] = Label(_("Clear"))
		self["key_green"] = Label(_("Delete"))
		self["key_yellow"] = Label(_("Zap & Close"))
		self["key_blue"] = Label(_("Config"))

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
			{
				"ok": self.zap,
				"cancel": self.close,
				"red": self.clear,
				"green": self.delete,
				"yellow": self.zapAndClose,
				"blue": self.config
			}, prio=-1)
		
		self.onLayoutFinish.append(self.buildList)

	def buildList(self):
		list = []
		for x in self.servicelist.history:
			if len(x) == 2: # Single-Bouquet
				ref = x[1]
			else: # Multi-Bouquet
				ref = x[2]
			info = self.serviceHandler.info(ref)
			if info:
				name = info.getName(ref).replace('\xc2\x86', '').replace('\xc2\x87', '')
				event = info.getEvent(ref)
				if event is not None:
					eventName = event.getEventName()
					if eventName is None:
						eventName = ""
				else:
					eventName = ""
			else:
				name = "N/A"
				eventName = ""
			list.append((name, eventName))
		list.reverse()
		self["list"].setList(list)

	def zap(self):
		length = len(self.servicelist.history)
		if length > 0:
			self.servicelist.history_pos = (length - self["list"].getIndex()) - 1
			self.servicelist.setHistoryPath()

	def clear(self):
		if self.allowChanges:
			for i in range(0, len(self.servicelist.history)):
				del self.servicelist.history[0]
			self.buildList()
			self.servicelist.history_pos = 0

	def delete(self):
		if self.allowChanges:
			length = len(self.servicelist.history)
			if length > 0:
				idx = (length - self["list"].getIndex()) - 1
				del self.servicelist.history[idx]
				self.buildList()
				currRef = self.session.nav.getCurrentlyPlayingServiceReference()
				idx = 0
				for x in self.servicelist.history:
					if len(x) == 2: # Single-Bouquet
						ref = x[1]
					else: # Multi-Bouquet
						ref = x[2]
					if ref == currRef:
						self.servicelist.history_pos = idx
						break
					else:
						idx += 1

	def zapAndClose(self):
		self.zap()
		self.close()

	def config(self):
		if self.allowChanges:
			self.session.open(ZapHistoryConfigurator)

	def isProtected(self):
		return config.ParentalControl.servicepinactive.value

	def pinEntered(self, result):
		if result is None:
			self.allowChanges = False
		elif not result:
			self.allowChanges = False
		else:
			self.allowChanges = True
