from Plugins.Plugin import PluginDescriptor
from Components.Network import iNetwork

# Don't remove this line! It's needed to remount shares at startup
from .AutoMount import iAutoMount
from . import _


plugin_path = ""


def NetworkBrowserMain(session, iface=None, **kwargs):
	from .NetworkBrowser import NetworkBrowser
	session.open(NetworkBrowser, iface, plugin_path)


def MountManagerMain(session, iface=None, **kwargs):
	from .MountManager import AutoMountManager
	session.open(AutoMountManager, iface, plugin_path)


def NetworkBrowserCallFunction(iface):
	interfaceState = iNetwork.getAdapterAttribute(iface, "up")
	if interfaceState is True:
		return NetworkBrowserMain
	else:
		return None


def MountManagerCallFunction(iface):
	return MountManagerMain


def RemountMain(session, iface=None, **kwargs):
	iAutoMount.getAutoMountPoints()


def RemountCallFunction(iface):
	if iNetwork.getAdapterAttribute(iface, "up"):
		return RemountMain


def Plugins(path, **kwargs):
	global plugin_path
	plugin_path = path
	return [
		PluginDescriptor(name=_("NetworkBrowser"), description=_("Search for network shares") + "\n", where=PluginDescriptor.WHERE_NETWORKSETUP, fnc={"ifaceSupported": NetworkBrowserCallFunction, "menuEntryName": lambda x: _("NetworkBrowser"), "menuEntryDescription": lambda x: _("Search for network shares...") + "\n"}),
		PluginDescriptor(name=_("MountManager"), description=_("Manage network shares") + "\n", where=PluginDescriptor.WHERE_NETWORKSETUP, fnc={"ifaceSupported": MountManagerCallFunction, "menuEntryName": lambda x: _("MountManager"), "menuEntryDescription": lambda x: _("Manage your network shares...") + "\n"}),
		PluginDescriptor(name=_("Mount again"), description=_("Attempt to mount shares again") + "\n", where=PluginDescriptor.WHERE_NETWORKSETUP,
			fnc={"ifaceSupported": RemountCallFunction,
				"menuEntryName": lambda x: _("Mount again"),
				"menuEntryDescription": lambda x: _("Attempt to recover lost mounts (in background)") + "\n"})
	]
