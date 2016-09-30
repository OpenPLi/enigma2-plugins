# -*- coding: utf-8 -*-
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import gettext

def localeInit():
	gettext.bindtextdomain("SimpleRSS", resolveFilename(SCOPE_PLUGINS, "Extensions/SimpleRSS/locale"))

def _(txt):
	t = gettext.dgettext("SimpleRSS", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)

