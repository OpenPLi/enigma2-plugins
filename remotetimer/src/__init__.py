from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
import os,gettext

def localeInit():
	gettext.bindtextdomain("remoteTimer", resolveFilename(SCOPE_PLUGINS, "Extensions/remoteTimer/locale"))

def _(txt):
	t = gettext.dgettext("remoteTimer", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

localeInit()
