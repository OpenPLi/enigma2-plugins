# for localized messages
from . import _
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Tools.Directories import fileExists
from Components.config import config, ConfigSubsection, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from time import strftime
import os

###############################################################################

config.plugins.logomanager = ConfigSubsection()
config.plugins.logomanager.path = ConfigSelection([("none",_("None")), ("/media/cf/bootlogos/",_("CF Drive")), ("/media/hdd/bootlogos/",_("Harddisk")), ("/media/usb/bootlogos/",_("USB Drive")),], default = "none")

from mimetypes import add_type
add_type("image/mvi", ".mvi")

#########

def filescan_open(list, session, **kwargs):
	print "[Logo Manager] filescan_open", list, kwargs
	session.open(LogoManagerScreen,file=list[0].path)

def start_from_filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	print "[Logo Manager] start_from_filescan", kwargs
	return \
		Scanner(mimetypes=["image/mvi"],
			paths_to_scan =
				[
					ScanPath(path = "", with_subdirs = False),
				],
			name = _("Logo Manager"),
			description = _("view bootlogo/mvi"),
			openfnc = filescan_open,
		)

###############################################################################

class LogoManagerScreen(Screen):
	skin = """
		<screen flags="wfNoBorder" position="60,450" size="600,29" title="Logo Manager" >
			<widget name="filelist" position="0,0" size="600,30"  />
		</screen>"""
	targets = [
				( _("bootlogo"), "/etc/enigma2/bootlogo.mvi"),
				( _("backdrop"), "/etc/enigma2/backdrop.mvi"),
				( _("radio"), "/usr/share/enigma2/radio.mvi"), 
				( _("switch off"), "/etc/enigma2/switchoff.mvi"),
				( _("reboot"), "/etc/enigma2/reboot.mvi")
				]

	def __init__(self, session, file = None):
		self.session = session
		self.skin = LogoManagerScreen.skin
		Screen.__init__(self, session)
		self.setTitle(_("Logo Manager"))
		self["filelist"] = MenuList([], enableWrapAround=True)
		self["filelist"].onSelectionChanged.append(self.showSelected)
		self["actions"] = ActionMap(["WizardActions", "DirectionActions","MenuActions","ShortcutActions","GlobalActions"],
		{
		"ok": self.showSelected,
		"back": self.Exit,
		"menu": self.openMenu,
		}, -1)

		self.current_service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.session.nav.stopService()

		self.available_logos_mode = False

		if file is None:
			self.setlist_to_avaiable()
			self.onShown.append(self.showSelected)
		elif os.path.isfile(file):
			e = lambda: self.reloadPictures([file])
			self.onShown.append(e)
			d = lambda: self.showMVI(file)
			self.onShown.append(d)

	def restoreOriginal(self):
		""" restoring original mvis"""
		self.restoreBootlogo()
		self.disableBackdrop()
		self.restoreRadio()
		self.disableSwitchoff()
		self.disableReboot()
		self.setlist_to_avaiable()
		self.showSelected()

	def Exit(self):
		""" quit me """
		self.session.nav.playService(self.current_service, adjust=False)
		self.close()

	def showSelected(self):
		""" show the currently selected MVI of the list """
		sel = self["filelist"].getCurrent()
		if sel is not None:
			self.showMVI(sel[1])

	def restoreBootlogo(self):
		if fileExists("/etc/enigma2/bootlogo.mvi"):
			try:
				os.remove("/etc/enigma2/bootlogo.mvi")
			except:
				pass

	def disableSwitchoff(self):
		if fileExists("/etc/enigma2/switchoff.mvi"):
			try:
				os.remove("/etc/enigma2/switchoff.mvi")
			except:
				pass
		if fileExists("/etc/rc0.d/K01bootlogo-switchoff"):
			try:
				os.remove("/etc/rc0.d/K01bootlogo-switchoff")
			except:
				pass

	def disableBackdrop(self):
		if fileExists("/etc/enigma2/backdrop.mvi"):
			try:
				os.remove("/etc/enigma2/backdrop.mvi")
			except:
				pass

	def disableReboot(self):
		if fileExists("/etc/enigma2/reboot.mvi"):
			try:
				os.remove("/etc/enigma2/reboot.mvi")
			except:
				pass
		if fileExists("/etc/rc6.d/K01bootlogo-reboot"):
			try:
				os.remove("/etc/rc6.d/K01bootlogo-reboot")
			except:
				pass

	def restoreRadio(self):
		if fileExists("/usr/share/enigma2/radio.mvi") and fileExists("/usr/share/enigma2/radio.mvi-orig"):
			try:
				os.remove("/usr/share/enigma2/radio.mvi")
			except:
				pass
			os.system("mv /usr/share/enigma2/radio.mvi-orig /usr/share/enigma2/radio.mvi")

	def addBootlogo(self):
		if fileExists("/usr/share/bootlogo.mvi"):
			data = strftime("%d-%m-%Y_%H-%M-%S")
			new_logo = "'%s''%s'-bootlogo.mvi" % (config.plugins.logomanager.path.value, data)
			ret = os.system("cp /usr/share/bootlogo.mvi '%s'" % new_logo)
			if ret == 0:
				self.setlist_to_avaiable()
				if fileExists("%s" % new_logo):
					self.showMVI(new_logo)

	def addRadio(self):
		if fileExists("/usr/share/enigma2/radio.mvi"):
			data = strftime("%d-%m-%Y_%H-%M-%S")
			new_logo = "'%s''%s'-radio.mvi" % (config.plugins.logomanager.path.value, data)
			ret = os.system("cp /usr/share/enigma2/radio.mvi '%s'" % new_logo)
			if ret == 0:
				self.setlist_to_avaiable()
				if fileExists(new_logo):
					self.showMVI(new_logo)

	def openMenu(self):
		""" opens up the Main Menu """
		menu = []
		if self.available_logos_mode:
			menu.append((_("Show available logos"), self.setlist_to_avaiable))
		else:
			menu.append((_("Install selected logo as..."), self.action_install))
			menu.append((_("Show active logos"), self.setlist_to_current))
			menu.append((_("Show available logos"), self.setlist_to_avaiable))
			if fileExists("/etc/enigma2/bootlogo.mvi"):
				menu.append((_("Reset bootlogo to default"), self.restoreBootlogo))
			if fileExists("/usr/share/enigma2/radio.mvi") and fileExists("/usr/share/enigma2/radio.mvi-orig"):
				menu.append((_("Reset radio to default"), self.restoreRadio))
			if fileExists("/etc/enigma2/backdrop.mvi"):
				menu.append((_("Disable backdrop"), self.disableBackdrop))
			if fileExists("/etc/enigma2/switchoff.mvi"):
				menu.append((_("Disable switch off"), self.disableSwitchoff))
			if fileExists("/etc/enigma2/reboot.mvi"):
				menu.append((_("Disable reboot"), self.disableReboot))
			if fileExists("/usr/share/bootlogo.mvi"):
				menu.append((_("Add default bootlogo to folder logos"), self.addBootlogo))
			if fileExists("/usr/share/enigma2/radio.mvi") and not fileExists("/usr/share/enigma2/radio.mvi-orig"):
				menu.append((_("Add default radio to folder logos"), self.addRadio))
			if fileExists("/etc/enigma2/bootlogo.mvi") or fileExists("/usr/share/enigma2/radio.mvi-orig") or fileExists("/etc/enigma2/switchoff.mvi") or fileExists("/etc/enigma2/backdrop.mvi") or fileExists("/etc/enigma2/reboot.mvi"):
				menu.append((_("Reset all logos to default"), self.restoreOriginal))
			sel = self["filelist"].getCurrent()
			if sel is not None:
				if sel[1] != "/usr/share/enigma2/radio.mvi" and sel[1] != "/usr/share/bootlogo.mvi":
					menu.append((_("Remove current logo"), self.removeCurrentLogo))
		menu.append((_("Open configuration"), self.openConfig))
		self.session.openWithCallback(self.selectedMenu, ChoiceBox, _("Please select a option:"), menu)

	def removeCurrentLogo(self):
		self.session.openWithCallback(self.confirmRemove, MessageBox,_("Really remove current logo of %s?") % config.plugins.logomanager.path.value, MessageBox.TYPE_YESNO)

	def confirmRemove(self, answer):
		if answer:
			sel = self["filelist"].getCurrent()
			if sel is not None:
				try:
					os.remove(sel[1])
					if not fileExists(sel[1]):
						self.setlist_to_avaiable()
						self.showSelected()
				except:
					pass

	def openConfig(self):
		self.session.open(LogoManagerConfigScreen)

	def selectedMenu(self,choice):
		if choice is not None:
			choice[1]()

	def setlist_to_current(self):
		""" fills the list with the target MVIs"""
		global plugin_path
		filelist =[]
		for i in self.targets:
			if fileExists(i[1]):
				filelist.append(i[1])
			else:
				if i[0] == _("bootlogo") and fileExists("/usr/share/bootlogo.mvi"):
					filelist.append("/usr/share/bootlogo.mvi")
		self.available_logos_mode = True
		self.reloadPictures(filelist)

	def setlist_to_avaiable(self):
		""" fills the list with all found new MVIs"""
		filelist =[]
		for i in os.listdir(config.plugins.logomanager.path.value):
			if i.endswith(".mvi"):
				filelist.append(config.plugins.logomanager.path.value + i)
		filelist.sort()
		self.available_logos_mode = False
		self.reloadPictures(filelist)

	def action_install(self):
		""" choicebox, to select target to install an mvi to"""
		self.session.openWithCallback(self.selectedTarget, ChoiceBox, _("Select target for logo:"), self.targets)

	def selectedTarget(self, choice):
		if choice is not None:
			self.installMVI(choice, self["filelist"].getCurrent()[1])

	def reloadPictures(self, filelist):
		""" build the menulist with givven files """
		list = []
		for i in filelist:
			list.append((i.split("/")[-1], i))
		self["filelist"].l.setList(list)

	def showMVI(self, mvifile):
		""" shows a mvi """
		print "[Logo Manager] playing MVI",mvifile
		os.system("/usr/bin/showiframe '%s'" % mvifile)

	def installMVI(self, target, sourcefile):
		""" installs a mvi by overwriting the target with a source mvi """
		print "[Logo Manager] installing %s as %s on %s" %(sourcefile, target[0], target[1])
		if target[0] == _("radio") and not fileExists("/usr/share/enigma2/radio.mvi-orig"):
			os.system("mv /usr/share/enigma2/radio.mvi /usr/share/enigma2/radio.mvi-orig")
		if fileExists(target[1]):
			try:
				os.remove(target[1])
			except:
				pass
		if target[0] == _("switch off") and not fileExists("/etc/rc0.d/K01bootlogo-switchoff"):
				cmd = "echo -e '#!/bin/sh\n\n[ -f /etc/enigma2/switchoff.mvi ] && /usr/bin/showiframe /etc/enigma2/switchoff.mvi' >> /etc/rc0.d/K01bootlogo-switchoff"
				os.system(cmd)
				if fileExists("/etc/rc0.d/K01bootlogo-switchoff"):
					os.chmod("/etc/rc0.d/K01bootlogo-switchoff", 0755)
		if target[0] == _("reboot") and not fileExists("/etc/rc6.d/K01bootlogo-reboot"):
				cmd = "echo -e '#!/bin/sh\n\n[ -f /etc/enigma2/reboot.mvi ] && /usr/bin/showiframe /etc/enigma2/reboot.mvi' >> /etc/rc6.d/K01bootlogo-reboot"
				os.system(cmd)
				if fileExists("/etc/rc6.d/K01bootlogo-reboot"):
					os.chmod("/etc/rc6.d/K01bootlogo-reboot", 0755)
		os.system("cp '%s' '%s'"%(sourcefile, target[1]))

class LogoManagerConfigScreen(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="530,200" title="LogoManager Setup" >
			<widget name="config" position="0,0" size="520,160" scrollbarMode="showOnDemand" />
			<widget name="buttonred" position="10,160" size="100,40" backgroundColor="red" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
			<widget name="buttongreen" position="120,160" size="100,40" backgroundColor="green" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		</screen>"""
	def __init__(self, session, args = 0):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("Logo manager setup"))
		self.list = []
		self.list.append(getConfigListEntry(_("Directory to scan for logos"), config.plugins.logomanager.path))
		ConfigListScreen.__init__(self, self.list)
		self["buttonred"] = Label(_("Cancel"))
		self["buttongreen"] = Label(_("OK"))
		self["setupActions"] = ActionMap(["SetupActions"],
		{
			"green": self.save,
			"red": self.cancel,
			"save": self.save,
			"cancel": self.cancel,
			"ok": self.save,
		}, -2)

	def save(self):
		dir = config.plugins.logomanager.path.value
		drive_path = dir[:-10]
		if os.path.isdir(drive_path) is True:
			bootlogos_dir = dir[:-1]
			os.system("mkdir %s" % bootlogos_dir)
		elif config.plugins.logomanager.path.value != "none":
			self.session.openWithCallback(self.exit, MessageBox, _("Not found directory '%s'!") % drive_path, MessageBox.TYPE_ERROR)
			config.plugins.logomanager.path.value = "none"
			config.plugins.logomanager.path.save()
			return
		config.plugins.logomanager.path.save()
		self.close()

	def exit(self, answer=None):
		self.close()

	def cancel(self):
		config.plugins.logomanager.path.cancel()
		self.close()

def main(session, **kwargs):
	if config.plugins.logomanager.path.value == "none" or os.path.isdir(config.plugins.logomanager.path.value) is not True:
		session.open(LogoManagerConfigScreen)
	else:
		session.open(LogoManagerScreen)

def Plugins(path, **kwargs):
    global plugin_path
    plugin_path = path
    return [
			PluginDescriptor(name = _("Logo Manager"), description = _("manage logos to display at boottime"), where = PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc = main),
			PluginDescriptor(name = _("Logo Manager"), where = PluginDescriptor.WHERE_FILESCAN, fnc = start_from_filescan)
			]
