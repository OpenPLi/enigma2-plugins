#
#  Partnerbox E2
#
#  $Id$
#
#  Coded by Dr.Best (c) 2009
#  Support: www.dreambox-tools.info
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#

from enigma import eListboxPythonMultiContent, eListbox, gFont, \
	RT_HALIGN_LEFT, RT_VALIGN_CENTER, getDesktop
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.MenuList import MenuList
from Components.Button import Button
from Components.config import config
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Screens.HelpMenu import HelpableScreen
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.config import ConfigSubsection, ConfigSubList, ConfigIP, ConfigInteger, ConfigSelection, ConfigText, ConfigYesNo, getConfigListEntry, configfile
from PartnerboxFunctions import sendPartnerBoxWebCommand
import skin
import os
from plugin import autoTimerAvailable
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Screens.VirtualKeyBoard import VirtualKeyBoard

# for localized messages
from . import _


def initPartnerboxEntryConfig():
	config.plugins.Partnerbox.Entries.append(ConfigSubsection())
	i = len(config.plugins.Partnerbox.Entries) - 1
	config.plugins.Partnerbox.Entries[i].name = ConfigText(default="Remote box", visible_width=50, fixed_size=False)
	config.plugins.Partnerbox.Entries[i].ip = ConfigIP(default=[192, 168, 0, 98])
	config.plugins.Partnerbox.Entries[i].port = ConfigInteger(default=80, limits=(1, 65555))
	config.plugins.Partnerbox.Entries[i].enigma = ConfigSelection(default="0", choices=[("0", _("Enigma 2")), ("1", _("Enigma 1"))])
	config.plugins.Partnerbox.Entries[i].type = ConfigSelection(default="4114", choices=[("4114", "4114"), ("4097", "4097")])
	config.plugins.Partnerbox.Entries[i].password = ConfigText(default="root", visible_width=50, fixed_size=False)
	config.plugins.Partnerbox.Entries[i].usewakeonlan = ConfigYesNo(default=False)
	config.plugins.Partnerbox.Entries[i].mac = ConfigText(default="00:00:00:00:00:00", fixed_size=False)
	config.plugins.Partnerbox.Entries[i].useinternal = ConfigSelection(default="1", choices=[("0", _("use external")), ("1", _("use internal"))])
	config.plugins.Partnerbox.Entries[i].zaptoservicewhenstreaming = ConfigYesNo(default=False)
	return config.plugins.Partnerbox.Entries[i]


def initConfig():
	count = config.plugins.Partnerbox.entriescount.value
	if count != 0:
		i = 0
		while i < count:
			initPartnerboxEntryConfig()
			i += 1


HD = False
if getDesktop(0).size().width() >= 1280:
	HD = True


class PartnerboxSetup(ConfigListScreen, Screen):
	if HD:
		skin = """ <screen position="center,center" size="700,400" title="Partnerbox Setup" >
				<widget name="config" position="10,10" size="680,330" scrollbarMode="showOnDemand" />
				<widget name="key_red" position="10,350" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;17"/>
				<widget name="key_green" position="300,350" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;17"/>
				<widget name="key_yellow" position="550,350" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;17"/>
				<ePixmap name="red" pixmap="skin_default/buttons/red.png" position="10,350" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
				<ePixmap name="green" pixmap="skin_default/buttons/green.png" position="300,350" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
				<ePixmap name="yellow" pixmap="skin_default/buttons/yellow.png" position="550,350" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
			</screen>"""
	else:
		skin = """ <screen position="center,center" size="550,400" title="Partnerbox Setup" >
				<widget name="config" position="20,10" size="510,330" scrollbarMode="showOnDemand" />
				<widget name="key_red" position="0,350" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;18"/>
				<widget name="key_green" position="140,350" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;18"/>
				<widget name="key_yellow" position="280,350" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;18"/>
				<ePixmap name="red" pixmap="skin_default/buttons/red.png" position="0,350" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
				<ePixmap name="green" pixmap="skin_default/buttons/green.png" position="140,350" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
				<ePixmap name="yellow" pixmap="skin_default/buttons/yellow.png" position="280,350" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
			</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.setTitle(_("Partnerbox Setup"))

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))
		self["key_yellow"] = Button(_("Partnerbox Entries"))
		ConfigListScreen.__init__(self, [])
		self.initConfig()
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.keySave,
			"cancel": self.keyClose,
			"red": self.keyClose,
			"ok": self.keySave,
			"yellow": self.PartnerboxEntries,
		}, -2)

	def initConfig(self):
		dx = 4 * " "
		self.list = []
		self.list.append(getConfigListEntry(_("Show 'RemoteTimer' in Eventinfo menu"), config.plugins.Partnerbox.enablepartnerboxeventinfomenu))
		if config.plugins.Partnerbox.enablepartnerboxeventinfomenu.value:
			self.list.append(getConfigListEntry(dx + _("Show 'RemoteTimer' in Event View context menu"), config.plugins.Partnerbox.enablepartnerboxeventinfocontextmenu))
		self.list.append(getConfigListEntry(_("Show 'RemoteTimer' in E-Menu"), config.plugins.Partnerbox.showremotetimerinextensionsmenu))
		self.list.append(getConfigListEntry(_("Show 'RemoteTV Player' in E-Menu"), config.plugins.Partnerbox.showremotetvinextensionsmenu))
		self.list.append(getConfigListEntry(_("Show 'Stream current Service' in E-Menu"), config.plugins.Partnerbox.showcurrentstreaminextensionsmenu))
		self.list.append(getConfigListEntry(_("Enable Partnerbox-Function in TimerEvent"), config.plugins.Partnerbox.enablepartnerboxintimerevent))
		if config.plugins.Partnerbox.enablepartnerboxintimerevent.value:
			self.list.append(getConfigListEntry(dx + _("Active boxes from local network only (using localhost names)"), config.plugins.Partnerbox.avahicompare))
			self.list.append(getConfigListEntry(dx + _("Enable first Partnerbox-entry in Timeredit as default"), config.plugins.Partnerbox.enabledefaultpartnerboxintimeredit))
			self.list.append(getConfigListEntry(dx + _("Enable VPS-Function in TimerEvent"), config.plugins.Partnerbox.enablevpsintimerevent))
		self.list.append(getConfigListEntry(_("Enable Partnerbox-Function in EPGList"), config.plugins.Partnerbox.enablepartnerboxepglist))
		if config.plugins.Partnerbox.enablepartnerboxepglist.value:
			self.list.append(getConfigListEntry(dx + _("Enable Red Button-Function in single/multi EPG"), config.plugins.Partnerbox.enablepartnerboxzapbuton))
			self.list.append(getConfigListEntry(dx + _("Show duration time for event"), config.plugins.Partnerbox.showremaingepglist))
			self.list.append(getConfigListEntry(dx + _("Show all icon for event in EPGList"), config.plugins.Partnerbox.allicontype))
		self.list.append(getConfigListEntry(_("Enable Partnerbox-Function in Channel Selector"), config.plugins.Partnerbox.enablepartnerboxchannelselector))
		if autoTimerAvailable:
			self.list.append(getConfigListEntry(_("Enable Partnerbox-AutoTimer function"), config.plugins.Partnerbox.showpartnerboxautotimerninmenu))
		self["config"].l.setList(self.list)

	def keySave(self):
		config.plugins.Partnerbox.showremotetvinextensionsmenu.save()
		config.plugins.Partnerbox.showcurrentstreaminextensionsmenu.save()
		config.plugins.Partnerbox.showremotetimerinextensionsmenu.save()
		config.plugins.Partnerbox.enablepartnerboxintimerevent.save()
		config.plugins.Partnerbox.enablepartnerboxepglist.save()
		config.plugins.Partnerbox.enablepartnerboxzapbuton.save()
		config.plugins.Partnerbox.enablepartnerboxchannelselector.save()
		config.plugins.Partnerbox.enabledefaultpartnerboxintimeredit.save()
		config.plugins.Partnerbox.enablepartnerboxeventinfomenu.save()
		config.plugins.Partnerbox.enablepartnerboxeventinfocontextmenu.save()
		config.plugins.Partnerbox.allicontype.save()
		config.plugins.Partnerbox.showremaingepglist.save()
		config.plugins.Partnerbox.enablevpsintimerevent.save()
		config.plugins.Partnerbox.showpartnerboxautotimerninmenu.save()
		config.plugins.Partnerbox.avahicompare.save()
		configfile.save()
		self.refreshPlugins()
		self.close(self.session)

	def keyClose(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close(self.session)

	def PartnerboxEntries(self):
		self.session.open(PartnerboxEntriesListConfigScreen)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.initConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.initConfig()

	def refreshPlugins(self):
		from Components.PluginComponent import plugins
		from Tools.Directories import SCOPE_PLUGINS, resolveFilename
		plugins.clearPluginList()
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))


class PartnerboxEntriesListConfigScreen(Screen, HelpableScreen):
	skin = """
		<screen position="center,center" size="550,400" title="Partnerbox: List of Entries" >
			<widget name="name" position="5,0" size="200,50" font="Regular;20" halign="left"/>
			<widget name="ip" position="215,0" size="140,50" font="Regular;20" halign="left"/>
			<widget name="port" position="350,0" size="80,50" font="Regular;20" halign="left"/>
			<widget name="type" position="430,0" size="120,50" font="Regular;20" halign="left"/>
			<widget name="entrylist" position="0,50" size="550,300" scrollbarMode="showOnDemand"/>

			<widget name="key_red" position="0,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_yellow" position="280,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="yellow" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_green" position="140,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="green" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_blue" position="420,350" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<ePixmap name="red" position="0,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap name="yellow" position="280,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<ePixmap name="green" position="140,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap name="blue" position="420,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
		</screen>"""

	def __init__(self, session, what=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.session = session
		self.setTitle(_("Partnerbox: List of Entries"))

		self["name"] = Button(_("Name"))
		self["ip"] = Button(_("IP"))
		self["port"] = Button(_("Port"))
		self["type"] = Button(_("Enigma Type"))
		self["key_red"] = Button(_("Add"))
		self["key_yellow"] = Button(_("Edit"))
		self["key_green"] = Button(_("Power"))
		self["key_blue"] = Button(_("Delete"))
		self["entrylist"] = PartnerboxEntryList([])
		self["PBPActions"] = HelpableActionMap(self, "PiPSetupActions",
			{
			 "size+": (self.powerOn, _("Wake up remote box")),
			 "size-": (self.powerStandby, _("Sleep remote box")),
			 }, -1)
		self["PBVActions"] = HelpableActionMap(self, "NumberActions",
			{
			"0": (self.startMoving, _("Enable/disable moving item")),
			"5": (self.powerMute, _("Mute remote box")),
			 }, -1)
		self["PBEditActions"] = HelpableActionMap(self, "DirectionActions",
			{
			"moveUp": (self.moveUp, _("Move item up")),
			"moveDown": (self.moveDown, _("Move item down")),
			 }, -1)
		self["actions"] = ActionMap(["WizardActions", "MenuActions", "ShortcutActions"],
			{
			 "ok": self.keyOK,
			 "back": self.keyClose,
			 "red": self.keyRed,
			 "yellow": self.keyYellow,
			 "blue": self.keyDelete,
			 "green": self.powerMenu,
			 "menu": self.powerMenu,
			 }, -1)
		self.edit = 0
		self.idx = 0
		self["h_prev"] = Pixmap()
		self["h_next"] = Pixmap()
		self.showPrevNext()
		self.what = what
		self.updateList()

	def updateList(self):
		self["entrylist"].buildList()

	def keyClose(self):
		self.close(self.session, self.what, None)

	def keyRed(self):
		self.session.openWithCallback(self.updateList, PartnerboxEntryConfigScreen, None)

	def keyOK(self):
		try:
			sel = self["entrylist"].l.getCurrentSelection()[0]
		except:
			sel = None
		nr = int(config.plugins.Partnerbox.entriescount.value)
		if nr > 1 and self.what == 2 or nr >= 1 and self.what is None:
				from plugin import RemoteTimer
				self.session.open(RemoteTimer, sel)
		else:
			self.close(self.session, self.what, sel)

	def keyYellow(self):
		try:
			sel = self["entrylist"].l.getCurrentSelection()[0]
		except:
			return
		self.session.openWithCallback(self.updateList, PartnerboxEntryConfigScreen, sel)

	def startMoving(self):
		self.edit = not self.edit
		self.idx = self["entrylist"].l.getCurrentSelectionIndex()
		self.showPrevNext()

	def showPrevNext(self):
		if self.edit:
			self["h_prev"].show()
			self["h_next"].show()
		else:
			self["h_prev"].hide()
			self["h_next"].hide()

	def moveUp(self):
		if self.edit and self.idx >= 1:
			self.moveDirection(-1)

	def moveDown(self):
		if self.edit and self.idx < config.plugins.Partnerbox.entriescount.value - 1:
			self.moveDirection(1)

	def moveDirection(self, direction):
		self["entrylist"].moveToIndex(self.idx)
		tmp = config.plugins.Partnerbox.Entries[self.idx]
		config.plugins.Partnerbox.Entries[self.idx] = config.plugins.Partnerbox.Entries[self.idx + direction]
		config.plugins.Partnerbox.Entries[self.idx + direction] = tmp
		self.updateList()
		self.idx += direction
		self["entrylist"].moveToIndex(self.idx)

	def keyDelete(self):
		try:
			sel = self["entrylist"].l.getCurrentSelection()[0]
		except:
			return
		self.session.openWithCallback(self.deleteConfirm, MessageBox, _("Really delete this Partnerbox Entry?"))

	def deleteConfirm(self, result):
		if not result:
			return
		sel = self["entrylist"].l.getCurrentSelection()[0]
		config.plugins.Partnerbox.entriescount.value = config.plugins.Partnerbox.entriescount.value - 1
		config.plugins.Partnerbox.entriescount.save()
		config.plugins.Partnerbox.Entries.remove(sel)
		config.plugins.Partnerbox.Entries.save()
		config.plugins.Partnerbox.save()
		configfile.save()
		self.updateList()

	def getPars(self, sel):
		password = sel.password.value
		username = "root"
		ip = "%d.%d.%d.%d" % tuple(sel.ip.value)
		port = sel.port.value
		enigma_type = int(sel.enigma.value)
		http = "http://%s:%d" % (ip, port)
		cmd = http
		cmd += enigma_type and "/cgi-bin/admin?command=" or "/web/powerstate?newstate="
		return password, username, http, cmd, enigma_type

	def getSelected(self):
		try:
			sel = self["entrylist"].l.getCurrentSelection()[0]
		except:
			sel = None
		return sel

	def powerMute(self):
		sel = self.getSelected()
		if sel is None:
			return
		(password, username, http, cmd, enigma_type) = self.getPars(sel)
		sCommand = http
		sCommand += enigma_type and "/cgi-bin/audio?mute=1" or "/web/vol?set=mute"
		sendPartnerBoxWebCommand(sCommand, None, 3, username, password)

	def powerOn(self):
		sel = self.getSelected()
		if sel is None:
			return
		(password, username, http, cmd, enigma_type) = self.getPars(sel)
		sCommand = cmd
		sCommand += enigma_type and "wakeup" or "4"
		sendPartnerBoxWebCommand(sCommand, None, 3, username, password)

	def powerStandby(self):
		sel = self.getSelected()
		if sel is None:
			return
		(password, username, http, cmd, enigma_type) = self.getPars(sel)
		sCommand = cmd
		sCommand += enigma_type and "standby" or "5"
		sendPartnerBoxWebCommand(sCommand, None, 3, username, password)

	def powerMenu(self):
		sel = self.getSelected()
		if sel is None:
			return
		menu = []
		menu.append((_("Wakeup"), 0))
		menu.append((_("Standby"), 1))
		menu.append((_("Restart enigma"), 2))
		menu.append((_("Restart"), 3))
		if int(sel.enigma.value) == 0:
			menu.append((_("Toggle Standby"), 4))
			menu.append((_("Deep Standby"), 5))
		else:
			menu.append((_("Shutdown"), 4))
		if sel.usewakeonlan.value and sel.enigma.value == "0":
			menu.append((_("Send Wake-on-LAN"), 6))
		if config.usage.remote_fallback_enabled.value:
			menu.append((_("Set as fallback remote receiver"), 10))
		menu.append((_("Mute"), 11))
		from Screens.ChoiceBox import ChoiceBox
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title=(_("Select operation for partnerbox") + ": " + "%s" % (sel.name.value)), list=menu)

	def menuCallback(self, choice):
		if choice is None:
			return
		sel = self.getSelected()
		if sel is None:
			return
		(password, username, http, cmd, enigma_type) = self.getPars(sel)
		sCommand = cmd
		if choice[1] == 0:
			sCommand += enigma_type and "wakeup" or "4"
		elif choice[1] == 1:
			sCommand += enigma_type and "standby" or "5"
		elif choice[1] == 2:
			sCommand += enigma_type and "restart" or "3"
		elif choice[1] == 3:
			sCommand += enigma_type and "reboot" or "2"
		elif choice[1] == 4:
			sCommand += enigma_type and "shutdown" or "0"
		elif choice[1] == 5:
			if enigma_type:
				return
			sCommand += "1"
		elif choice[1] == 6:
			self.sendWOL(sel.mac.value)
			return
		elif choice[1] == 10:
			ip = "%d.%d.%d.%d" % tuple(sel.ip.value)
			self.setFallbackTuner(sel.name.value, ip)
			return
		elif choice[1] == 11:
			sCommand = http
			sCommand += enigma_type and "/cgi-bin/audio?mute=1" or "/web/vol?set=mute"
		else:
			return
		sendPartnerBoxWebCommand(sCommand, None, 3, username, password)

	def GetIPsFromNetworkInterfaces(self):
		import socket
		import fcntl
		import struct
		import array
		import sys
		is_64bits = sys.maxsize > 2**32
		struct_size = 40 if is_64bits else 32
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		max_possible = 8 # initial value
		while True:
			_bytes = max_possible * struct_size
			names = array.array('B')
			for i in range(0, _bytes):
				names.append(0)
			outbytes = struct.unpack('iL', fcntl.ioctl(
				s.fileno(),
				0x8912,  # SIOCGIFCONF
				struct.pack('iL', _bytes, names.buffer_info()[0])
			))[0]
			if outbytes == _bytes:
				max_possible *= 2
			else:
				break
		namestr = names.tostring()
		ifaces = []
		for i in range(0, outbytes, struct_size):
			iface_name = bytes.decode(namestr[i:i + 16]).split('\0', 1)[0].encode('ascii')
			if iface_name != 'lo':
				iface_addr = socket.inet_ntoa(namestr[i + 20:i + 24])
				ifaces.append((iface_name, iface_addr))
		return ifaces

	def sendWOL(self, mac):
		ifaces_list = self.GetIPsFromNetworkInterfaces()
		if ifaces_list:
			for iface in ifaces_list:
				os.system("ether-wake -i %s %s" % (iface[0], mac))

	def setFallbackTuner(self, name, ip):
		if not ip:
			return

		def fallbackConfirm(result):
			if not result:
				return
			config.usage.remote_fallback.value = "http://%s:8001" % ip
			config.usage.remote_fallback.save()
		self.session.openWithCallback(fallbackConfirm, MessageBox, _("Set %s as fallback remote receiver?") % name)


class PartnerboxEntryList(MenuList):
	def __init__(self, list, enableWrapAround=True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = skin.fonts.get("PartnerBoxEntryList0", ("Regular", 20, 20))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.ItemHeight = int(font[2])
		font = skin.fonts.get("PartnerBoxEntryList1", ("Regular", 18))
		self.l.setFont(1, gFont(font[0], font[1]))

	def postWidgetCreate(self, instance):
		MenuList.postWidgetCreate(self, instance)
		instance.setItemHeight(self.ItemHeight)

	def buildList(self):
		self.list = []
		for c in config.plugins.Partnerbox.Entries:
			res = [c]
			x, y, w, h = skin.parameters.get("PartnerBoxEntryListName", (5, 0, 150, 20))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(c.name.value)))
			ip = "%d.%d.%d.%d" % tuple(c.ip.value)
			x, y, w, h = skin.parameters.get("PartnerBoxEntryListIP", (120, 0, 150, 20))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(ip)))
			port = "%d" % (c.port.value)
			x, y, w, h = skin.parameters.get("PartnerBoxEntryListPort", (270, 0, 100, 20))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(port)))
			if int(c.enigma.value) == 0:
				e_type = "Enigma2"
			else:
				e_type = "Enigma1"
			x, y, w, h = skin.parameters.get("PartnerBoxEntryListType", (410, 0, 100, 20))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(e_type)))
			self.list.append(res)
		self.l.setList(self.list)
		self.moveToIndex(0)


class PartnerboxEntryConfigScreen(ConfigListScreen, Screen):
	skin = """
		<screen name="PartnerboxEntryConfigScreen" position="center,center" size="560,400" title="Partnerbox: Edit Entry">
			<widget name="config" position="10,10" size="540,330" scrollbarMode="showOnDemand" />
			<ePixmap name="red" position="0,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap name="green" position="140,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap name="yellow" position="280,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<ePixmap name="blue" position="420,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />

			<widget name="key_red" position="0,350" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_green" position="140,350" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_yellow" position="280,350" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_blue" position="420,350" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="VKeyIcon" render="Pixmap" pixmap="skin_default/buttons/key_text.png" position="30,325" zPosition="10" size="35,25" transparent="1" alphatest="on">
				<convert type="ConditionalShowHide"/>
			</widget>
		</screen>"""

	def __init__(self, session, entry):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("Partnerbox: Edit Entry"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.keySave,
			"red": self.keyCancel,
			"yellow": self.getMAC,
			"blue": self.keyDelete,
			"cancel": self.keyCancel
		}, -2)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))
		self["key_yellow"] = Button()
		self["key_blue"] = Button(_("Delete"))

		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		if entry is None:
			self.newmode = 1
			self.current = initPartnerboxEntryConfig()
		else:
			self.newmode = 0
			self.current = entry

		ConfigListScreen.__init__(self, [], session, on_change=self.changedEntry)

		self.initConfig()

	def initConfig(self):
		list = [
			getConfigListEntry(_("Name"), self.current.name),
			getConfigListEntry(_("IP"), self.current.ip),
			getConfigListEntry(_("Port"), self.current.port),
			getConfigListEntry(_("Service type"), self.current.type),
			getConfigListEntry(_("Password"), self.current.password),
			getConfigListEntry(_("Servicelists/EPG"), self.current.useinternal),
			getConfigListEntry(_("Zap to service when streaming"), self.current.zaptoservicewhenstreaming)
		]
		self["key_yellow"].setText(" ")
		self.mac = getConfigListEntry(_("MAC"), self.current.mac)
		self.useWOL = _("Use Wake-on-LAN")
		if self.current.enigma.value == "0":
			list.append(getConfigListEntry(self.useWOL, self.current.usewakeonlan))
			if self.current.usewakeonlan.value:
				list.append(self.mac)
				self["key_yellow"].setText(_("Get MAC"))
		self["config"].list = list
		self["config"].l.setList(list)

	def changedEntry(self):
		if self["config"].getCurrent()[0] == self.useWOL:
			self.initConfig()

	def keySave(self):
		if self.newmode == 1:
			config.plugins.Partnerbox.entriescount.value = config.plugins.Partnerbox.entriescount.value + 1
			config.plugins.Partnerbox.entriescount.save()
		ConfigListScreen.keySave(self)
		if self.current.enigma.value == "1":
			self.current.enigma.value = "0"
			self.current.enigma.save()
		config.plugins.Partnerbox.save()
		configfile.save()
		self.close()

	def keyCancel(self):
		if self.newmode == 1:
			config.plugins.Partnerbox.Entries.remove(self.current)
		ConfigListScreen.cancelConfirm(self, True)

	def keyDelete(self):
		if self.newmode == 1:
			self.keyCancel()
		else:
			self.session.openWithCallback(self.deleteConfirm, MessageBox, _("Really delete this Partnerbox Entry?"))

	def deleteConfirm(self, result):
		if not result:
			return
		config.plugins.Partnerbox.entriescount.value = config.plugins.Partnerbox.entriescount.value - 1
		config.plugins.Partnerbox.entriescount.save()
		config.plugins.Partnerbox.Entries.remove(self.current)
		config.plugins.Partnerbox.Entries.save()
		config.plugins.Partnerbox.save()
		configfile.save()
		self.close()

	def getMAC(self):
		if not self.current.usewakeonlan.value and self.current.enigma.value == "1":
			return
		ip = "%s.%s.%s.%s" % (tuple(self.current.ip.value))
		pcMAC = self.readMac(ip)
		if pcMAC is not None:
			self.current.mac.value = pcMAC
			self["config"].invalidate(self.mac)
		else:
			res = os.system("ping -c 2 -W 1 %s >/dev/null 2>&1" % (ip))
			if not res:
				pcMAC = self.readMac(ip)
				if pcMAC is not None:
					self.current.mac.value = pcMAC
					self["config"].invalidate(self.mac)

	def readMac(self, ip):
		pcMAC = None
		file = open("/proc/net/arp", "r")
		while True:
			entry = file.readline().strip()
			if entry == "":
				break
			if entry.find(ip) == 0:
				p = entry.find(':')
				pcMAC = entry[p - 2:p + 15]
				if pcMAC != "00:00:00:00:00:00":
					file.close()
					return pcMAC
		file.close()
		return None
