from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
import os,gettext

def localeInit():
	gettext.bindtextdomain("DreamExplorer", resolveFilename(SCOPE_PLUGINS, "Extensions/DreamExplorer/locale"))

def _(txt):
	t = gettext.dgettext("DreamExplorer", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

localeInit()