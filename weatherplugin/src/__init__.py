# -*- coding: utf-8 -*-
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
import os,gettext

def localeInit():
	gettext.bindtextdomain("WeatherPlugin", resolveFilename(SCOPE_PLUGINS, "Extensions/WeatherPlugin/locale"))

def _(txt):
	t = gettext.dgettext("WeatherPlugin", txt)
	if t == txt:
		print "[WeatherPlugin] fallback to default translation for", txt
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)
