# -*- coding: utf-8 -*-
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from os import environ as os_environ
import gettext

def localeInit():
	gettext.bindtextdomain("VirtualZap", resolveFilename(SCOPE_PLUGINS, "Extensions/VirtualZap/locale"))

def _(txt):
	t = gettext.dgettext("VirtualZap", txt)
	if t == txt:
		print "[VirtualZap] fallback to default translation for", txt
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)

