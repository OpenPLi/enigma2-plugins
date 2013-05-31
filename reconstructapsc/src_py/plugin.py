from Plugins.Plugin import PluginDescriptor
from . import _

def main(session, service, **kwargs):
	import ui
	session.open(ui.ReconstructApSc, service, **kwargs)

def Plugins(**kwargs):
	return PluginDescriptor(name="ReconstructApSc", description=_("Reconstruct AP/SC ..."), where = PluginDescriptor.WHERE_MOVIELIST, fnc=main)
