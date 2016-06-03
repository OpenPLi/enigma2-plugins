# -*- coding: utf-8 -*-
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
import gettext

def localeInit():
	gettext.bindtextdomain("Transmission", resolveFilename(SCOPE_PLUGINS, "Extensions/Transmission/locale"))

def _(txt):
	t = gettext.dgettext("Transmission", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)

