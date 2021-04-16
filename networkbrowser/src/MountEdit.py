# -*- coding: utf-8 -*-
# for localized messages
from __init__ import _
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigIP, NoSave, ConfigText, ConfigEnableDisable, ConfigPassword, ConfigSelection, getConfigListEntry, ConfigYesNo
from Components.ConfigList import ConfigListScreen
from Components.Pixmap import Pixmap
from Components.ActionMap import ActionMap, NumberActionMap
from AutoMount import iAutoMount, AutoMount
from Components.Sources.Boolean import Boolean

# helper function to convert ips from a sring to a list of ints


def convertIP(ip):
	try:
		strIP = ip.split('.')
		ip = []
		for x in strIP:
			ip.append(int(x))
	except:
		ip = [0, 0, 0, 0]
	return ip


class AutoMountEdit(Screen, ConfigListScreen):
	skin = """
		<screen name="AutoMountEdit" position="center,center" size="560,450" title="MountEdit">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="config" position="5,50" size="550,250" zPosition="1" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,420" zPosition="1" size="560,2" />
			<widget source="introduction" render="Label" position="10,430" size="540,21" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1"/>
			<widget name="VKeyIcon" pixmap="skin_default/buttons/key_text.png" position="10,430" zPosition="10" size="35,25" transparent="1" alphatest="on" />
			<widget name="HelpWindow" pixmap="skin_default/vkey_icon.png" position="160,350" zPosition="1" size="1,1" transparent="1" alphatest="on" />
		</screen>"""

	def __init__(self, session, plugin_path, mountinfo=None):
		self.skin_path = plugin_path
		self.session = session
		Screen.__init__(self, self.session)

		self.mountinfo = mountinfo
		if self.mountinfo is None:
			#Initialize blank mount enty
			self.mountinfo = {'isMounted': False, 'active': False, 'ip': False, 'host': False, 'sharename': False, 'sharedir': False, 'username': False, 'password': False, 'mounttype': False, 'options': False, 'hdd_replacement': False}

		self.applyConfigRef = None
		self.updateConfigRef = None
		self.mounts = iAutoMount.getMountsList()
		self.createConfig()

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.ok,
			"back": self.close,
			"cancel": self.close,
			"red": self.close,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session)
		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)
		# Initialize Buttons
		self["VKeyIcon"] = Boolean(False)
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["introduction"] = StaticText(_("Press OK to activate the settings."))
		self["key_red"] = StaticText(_("Cancel"))

	def layoutFinished(self):
		self.setTitle(_("Mounts editor"))

	def exit(self):
		self.close()

	def createConfig(self):
		self.sharenameEntry = None
		self.mounttypeEntry = None
		self.activeEntry = None
		self.ipEntry = None
		self.hostEntry = None
		self.sharedirEntry = None
		self.optionsEntry = None
		self.usernameEntry = None
		self.passwordEntry = None
		self.hdd_replacementEntry = None
		self.sharetypelist = [("nfs", _("NFS share")), ("cifs", _("CIFS share"))]

		mounttype = self.mountinfo.get('mounttype')
		if not mounttype:
			mounttype = "nfs"
		active = self.mountinfo.get('active', 'True') == 'True'
		# Not that "host" takes precedence over "ip"
		host = self.mountinfo.get('host', "")
		if not host:
			# In case host is something funky like False or None
			host = ''
		try:
			ip = convertIP(self.mountinfo['ip'])
		except Exception, ex:
			print "[NWB] Invalid IP", ex
			ip = [0, 0, 0, 0]
		sharename = self.mountinfo.get('sharename', "Sharename")
		sharedir = self.mountinfo.get('sharedir', "/media/hdd")
		username = self.mountinfo.get('username', "")
		password = self.mountinfo.get('password', "")
		hdd_replacement = self.mountinfo.get('hdd_replacement', False)
		if hdd_replacement == 'True':
			hdd_replacement = True
		else:
			hdd_replacement = False
		if sharename is False:
			sharename = "Sharename"
		if sharedir is False:
			sharedir = "/media/hdd"
		if mounttype == "nfs":
			defaultOptions = "rw,nolock,soft"
		else:
			defaultOptions = "rw"
		if username is False:
			username = ""
		if password is False:
			password = ""
		options = self.mountinfo.get('options', defaultOptions)

		self.activeConfigEntry = NoSave(ConfigEnableDisable(default=active))
		self.ipConfigEntry = NoSave(ConfigIP(default=ip))
		self.hostConfigEntry = NoSave(ConfigText(default=host, visible_width=50, fixed_size=False))
		self.sharenameConfigEntry = NoSave(ConfigText(default=sharename, visible_width=50, fixed_size=False))
		self.sharedirConfigEntry = NoSave(ConfigText(default=sharedir, visible_width=50, fixed_size=False))
		self.optionsConfigEntry = NoSave(ConfigText(default=defaultOptions, visible_width=50, fixed_size=False))
		if options is not False:
			self.optionsConfigEntry.value = options
		self.usernameConfigEntry = NoSave(ConfigText(default=username, visible_width=50, fixed_size=False))
		self.passwordConfigEntry = NoSave(ConfigPassword(default=password, visible_width=50, fixed_size=False))
		self.mounttypeConfigEntry = NoSave(ConfigSelection(self.sharetypelist, default=mounttype))
		self.hdd_replacementConfigEntry = NoSave(ConfigYesNo(default=hdd_replacement))

	def createSetup(self):
		self.list = []
		self.activeEntry = getConfigListEntry(_("Active"), self.activeConfigEntry)
		self.list.append(self.activeEntry)
		self.sharenameEntry = getConfigListEntry(_("Local mountpoint"), self.sharenameConfigEntry)
		self.list.append(self.sharenameEntry)
		self.mounttypeEntry = getConfigListEntry(_("Mount type"), self.mounttypeConfigEntry)
		self.list.append(self.mounttypeEntry)
		self.ipEntry = getConfigListEntry(_("Server IP"), self.ipConfigEntry)
		self.list.append(self.ipEntry)
		self.hostEntry = getConfigListEntry(_("Host name"), self.hostConfigEntry)
		self.list.append(self.hostEntry)
		self.sharedirEntry = getConfigListEntry(_("Server share"), self.sharedirConfigEntry)
		self.list.append(self.sharedirEntry)
		self.hdd_replacementEntry = getConfigListEntry(_("use as HDD replacement"), self.hdd_replacementConfigEntry)
		self.list.append(self.hdd_replacementEntry)
		if self.optionsConfigEntry.value == self.optionsConfigEntry.default:
			if self.mounttypeConfigEntry.value == "cifs":
				self.optionsConfigEntry = NoSave(ConfigText(default="rw", visible_width=50, fixed_size=False))
			else:
				self.optionsConfigEntry = NoSave(ConfigText(default="rw,nolock,soft", visible_width=50, fixed_size=False))
		self.optionsEntry = getConfigListEntry(_("Mount options"), self.optionsConfigEntry)
		self.list.append(self.optionsEntry)
		if self.mounttypeConfigEntry.value == "cifs":
			self.usernameEntry = getConfigListEntry(_("Username"), self.usernameConfigEntry)
			self.list.append(self.usernameEntry)
			self.passwordEntry = getConfigListEntry(_("Password"), self.passwordConfigEntry)
			self.list.append(self.passwordEntry)

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		if self["config"].getCurrent() == self.mounttypeEntry:
			self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def ok(self):
		current = self["config"].getCurrent()
		if current == self.sharenameEntry or current == self.sharedirEntry or current == self.sharedirEntry or current == self.optionsEntry or current == self.usernameEntry or current == self.passwordEntry:
			if current[1].help_window.instance is not None:
				current[1].help_window.instance.hide()
		sharename = self.sharenameConfigEntry.value
		if sharename in self.mounts:
			self.session.openWithCallback(self.updateConfig, MessageBox, (_("A mount entry with this name already exists!\nUpdate existing entry and continue?\n")))
		else:
			self.session.openWithCallback(self.applyConfig, MessageBox, (_("Are you sure you want to save this network mount?\n\n")))

	def updateConfig(self, ret=False):
		if (ret == True):
			sharedir = None
			if self.sharedirConfigEntry.value.startswith("/"):
				sharedir = self.sharedirConfigEntry.value[1:]
			else:
				sharedir = self.sharedirConfigEntry.value
			iAutoMount.setMountsAttribute(self.sharenameConfigEntry.value, "sharename", self.sharenameConfigEntry.value)
			iAutoMount.setMountsAttribute(self.sharenameConfigEntry.value, "active", self.activeConfigEntry.value)
			iAutoMount.setMountsAttribute(self.sharenameConfigEntry.value, "host", self.hostConfigEntry.getText())
			iAutoMount.setMountsAttribute(self.sharenameConfigEntry.value, "ip", self.ipConfigEntry.getText())
			iAutoMount.setMountsAttribute(self.sharenameConfigEntry.value, "sharedir", sharedir)
			iAutoMount.setMountsAttribute(self.sharenameConfigEntry.value, "mounttype", self.mounttypeConfigEntry.value)
			iAutoMount.setMountsAttribute(self.sharenameConfigEntry.value, "options", self.optionsConfigEntry.value)
			iAutoMount.setMountsAttribute(self.sharenameConfigEntry.value, "username", self.usernameConfigEntry.value)
			iAutoMount.setMountsAttribute(self.sharenameConfigEntry.value, "password", self.passwordConfigEntry.value)
			iAutoMount.setMountsAttribute(self.sharenameConfigEntry.value, "hdd_replacement", self.hdd_replacementConfigEntry.value)

			self.updateConfigRef = None
			self.updateConfigRef = self.session.openWithCallback(self.updateConfigfinishedCB, MessageBox, _("Please wait while updating your network mount..."), type=MessageBox.TYPE_INFO, enable_input=False)
			iAutoMount.writeMountsConfig()
			iAutoMount.getAutoMountPoints(self.updateConfigDataAvail)
		else:
			self.close()

	def updateConfigDataAvail(self, data):
		if data is True:
			self.updateConfigRef.close(True)

	def updateConfigfinishedCB(self, data):
		if data is True:
			self.session.openWithCallback(self.Updatefinished, MessageBox, _("Your network mount has been updated."), type=MessageBox.TYPE_INFO, timeout=10)

	def Updatefinished(self, data):
		if data is not None:
			if data is True:
				self.close()

	def applyConfig(self, ret=False):
		if (ret == True):
			data = {'isMounted': False, 'active': False, 'ip': False, 'sharename': False, 'sharedir': False,
					'username': False, 'password': False, 'mounttype': False, 'options': False, 'hdd_replacement': False}
			data['active'] = self.activeConfigEntry.value
			data['host'] = self.hostConfigEntry.getText()
			data['ip'] = self.ipConfigEntry.getText()
			data['sharename'] = self.sharenameConfigEntry.value.strip()
			if self.sharedirConfigEntry.value.startswith("/"):
				data['sharedir'] = self.sharedirConfigEntry.value[1:]
			else:
				data['sharedir'] = self.sharedirConfigEntry.value
			data['options'] = self.optionsConfigEntry.value
			data['mounttype'] = self.mounttypeConfigEntry.value
			data['username'] = self.usernameConfigEntry.value
			data['password'] = self.passwordConfigEntry.value
			data['hdd_replacement'] = self.hdd_replacementConfigEntry.value
			self.applyConfigRef = None
			self.applyConfigRef = self.session.openWithCallback(self.applyConfigfinishedCB, MessageBox, _("Please wait for activation of your network mount..."), type=MessageBox.TYPE_INFO, enable_input=False)
			iAutoMount.automounts[self.sharenameConfigEntry.value] = data
			iAutoMount.writeMountsConfig()
			iAutoMount.getAutoMountPoints(self.applyConfigDataAvail)
		else:
			self.close()

	def applyConfigDataAvail(self, data):
		if data is True:
			self.applyConfigRef.close(True)

	def applyConfigfinishedCB(self, data):
		if data is True:
			self.session.openWithCallback(self.applyfinished, MessageBox, _("Your network mount has been activated."), type=MessageBox.TYPE_INFO, timeout=10)

	def applyfinished(self, data):
		if data is True:
			self.close()
