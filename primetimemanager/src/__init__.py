# -*- coding: utf-8 -*-
from Components.Language import language
import gettext
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE

def localeInit():
	lang = language.getLanguage()
	gettext.bindtextdomain("PrimeTimeManager", resolveFilename(SCOPE_PLUGINS, "Extensions/PrimeTimeManager/locale"))

def _(txt):
	t = gettext.dgettext("PrimeTimeManager", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)

