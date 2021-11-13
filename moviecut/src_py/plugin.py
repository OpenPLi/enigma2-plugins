from Plugins.Plugin import PluginDescriptor
from Plugins.Extensions.MovieCut.__init__ import _
import os


def main(session, service, **kwargs):
	from Plugins.Extensions.MovieCut import ui
	# Hack to make sure it is executable
	if not os.access(ui.mcut_path, os.X_OK):
		os.chmod(ui.mcut_path, 493)
	session.open(ui.MovieCut, service, **kwargs)


def Plugins(**kwargs):
	return PluginDescriptor(name="MovieCut", description=_("Execute cuts..."), where=PluginDescriptor.WHERE_MOVIELIST, fnc=main)
