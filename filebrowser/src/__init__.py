from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from os import environ as os_environ
import gettext


def localeInit():
	gettext.bindtextdomain("Filebrowser", resolveFilename(SCOPE_PLUGINS, "Extensions/Filebrowser/locale"))


def _(txt):
	t = gettext.dgettext("Filebrowser", txt)
	if t == txt:
		#print("[Filebrowser] fallback to default translation for", txt)
		t = gettext.gettext(txt)
	return t


localeInit()
language.addCallback(localeInit)
