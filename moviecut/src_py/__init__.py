# -*- coding: utf-8 -*-
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from os import environ as os_environ
import gettext

def localeInit():
	gettext.bindtextdomain("MovieCut", resolveFilename(SCOPE_PLUGINS, "Extensions/MovieCut/locale"))

def _(txt):
	t = gettext.dgettext("MovieCut", txt)
	if t == txt:
		print "[MovieCut] fallback to default translation for", txt
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)
