from . import _
from Screens.Screen import Screen
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Tools.Directories import fileExists
import os

transmission_sh = "/etc/init.d/transmission.sh"
transinfo_sh = "/usr/lib/enigma2/python/Plugins/Extensions/Transmission/trans_info.sh"
swap_sh = "/usr/lib/enigma2/python/Plugins/Extensions/Transmission/trans_swap.sh"
pause_sh = "/usr/lib/enigma2/python/Plugins/Extensions/Transmission/trans_start_stop_down.sh"

class Transmission(Screen):
	skin = """
	<screen position="center,center" size="720,440" title="Transmission menu" >
		<widget name="menu" position="10,10" size="700,420" scrollbarMode="showOnDemand" />
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.setTitle(_("Transmission menu"))
		list = []
		list.append((_("Information transmission download"), "info"))
		list.append((_("Start transmission"), "start"))
		list.append((_("Stop transmission"), "stop"))
		list.append((_("Restart transmission"), "restart"))
		list.append((_("Enable transmission autostart"), "enable"))
		list.append((_("Disable transmission autostart"), "disable"))
		list.append((_("Pause all downloads"), "pause"))
		list.append((_("Unpause all downloads"), "unpause"))
		list.append((_("Enable auto queue downloads"), "on"))
		list.append((_("Disable auto queue downloads"), "off"))
		list.append((_("Enabled SWAP when start transmission"), "enabled"))
		list.append((_("Create SWAP '/media/hdd/swapfile'"), "create"))
		list.append((_("Not enabled SWAP when start transmission"), "disabled"))
		list.append((_("Stop transmission after downloads (only queue works)"), "stop_trans"))
		list.append((_("Don't stop transmission after downloads (only queue works)"), "dont_stop_trans"))
		list.append((_("About transmission version"), "about_transmission"))
		self["menu"] = MenuList(list)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.run, "cancel": self.close}, -1)

	def run(self):
		returnValue = self["menu"].l.getCurrentSelection() and self["menu"].l.getCurrentSelection()[1]
		if returnValue is not None:
			cmd = "cp /usr/lib/enigma2/python/Plugins/Extensions/Transmission/transmission.sh %s && chmod 755 %s" % (transmission_sh, transmission_sh)
			os.system(cmd)
			if returnValue is "info":
				self.session.open(Console,_("Information transmission download"),["chmod 755 %s && %s" % (transinfo_sh, transinfo_sh)])
			elif returnValue is "pause":
				self.session.open(Console,_("Pause all downloads"),["chmod 755 %s && %s pause" % (pause_sh, pause_sh)])
			elif returnValue is "unpause":
				self.session.open(Console,_("Unpause all downloads"),["chmod 755 %s && %s unpause" % (pause_sh, pause_sh)])
			elif returnValue is "start":
				self.session.open(Console,_("Start transmission"),["%s start" % transmission_sh])
			elif returnValue is "stop":
				self.session.open(Console,_("Stop transmission"),["%s stop" % transmission_sh])
			elif returnValue is "restart":
				self.session.open(Console,_("Restart transmission"),["%s restart" % transmission_sh])
			elif returnValue is "enable":
				self.session.open(Console,_("Enable transmission autostart"),["%s enable" % transmission_sh])
			elif returnValue is "disable":
				self.session.open(Console,_("Disable transmission autostart"),["%s disable" % transmission_sh])
			elif returnValue is "on":
				self.session.open(Console,_("Enable auto queue downloads"),["chmod 755 %s && %s on" % (swap_sh, swap_sh)])
			elif returnValue is "off":
				self.session.open(Console,_("Disable auto queue downloads"),["chmod 755 %s && %s off" % (swap_sh, swap_sh)])
			elif returnValue is "enabled":
				self.session.open(Console,_("Enabled SWAP when start transmission"),["chmod 755 %s && %s enabled" % (swap_sh, swap_sh)])
			elif returnValue is "create":
				self.session.open(Console,_("Create SWAP '/media/hdd/swapfile'"),["chmod 755 %s && %s create" % (swap_sh, swap_sh)])
			elif returnValue is "disabled":
				self.session.open(Console,_("Not enabled SWAP when start transmission"),["chmod 755 %s && %s disabled" % (swap_sh, swap_sh)])
			elif returnValue is "stop_trans":
				self.session.open(Console,_("Stop transmission after downloads (only queue works)"),["chmod 755 %s && %s stop_trans" % (swap_sh, swap_sh)])
			elif returnValue is "dont_stop_trans":
				self.session.open(Console,_("Don't stop transmission after downloads (only queue works)"),["chmod 755 %s && %s dont_stop_trans" % (swap_sh, swap_sh)])
			elif returnValue is "about_transmission":
				if fileExists("/usr/bin/transmission-daemon"):
					self.session.open(Console,_("About transmission version"),["transmission-daemon -V \n", "echo Default login:root/password:root"])
				else:
					self.session.openWithCallback(self.InstallNow, MessageBox, _("transmission-daemon not installed!\nInstall now?"), MessageBox.TYPE_YESNO)

	def InstallNow(self, answer):
		if answer:
			self.session.openWithCallback(self.close, Console,_("transmission-daemon"),["opkg update && opkg install transmission && opkg install transmission-client"])

def main(session, **kwargs):
	session.open(Transmission)

def Plugins(path,**kwargs):
	return [PluginDescriptor(name=_("Transmission"), description=_("Bittorrent client for enigma2"), where = PluginDescriptor.WHERE_PLUGINMENU,icon="transmission.png",fnc = main),
		PluginDescriptor(name=_("Transmission"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main)]
