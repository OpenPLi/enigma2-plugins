# -*- coding: utf-8 -*-
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from os import environ as os_environ
import gettext

def localeInit():
	gettext.bindtextdomain("WerbeZapper", resolveFilename(SCOPE_PLUGINS, "Extensions/WerbeZapper/locale"))

def _(txt):
	t = gettext.dgettext("WerbeZapper", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)

