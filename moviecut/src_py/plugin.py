from Plugins.Plugin import PluginDescriptor
from .__init__ import _
from os import access, chmod, X_OK


def main(session, service, **kwargs):
	from Plugins.Extensions.MovieCut import ui
	# Hack to make sure it is executable
	if not access(ui.mcut_path, X_OK):
		chmod(ui.mcut_path, 493)
	session.open(ui.MovieCut, service, **kwargs)


def Plugins(**kwargs):
	return PluginDescriptor(name="MovieCut", description=_("Execute cuts..."), where=PluginDescriptor.WHERE_MOVIELIST, fnc=main)
