# -*- coding: utf-8 -*-
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from os import environ as os_environ
import gettext

def localeInit():
	gettext.bindtextdomain("AutoTimer", resolveFilename(SCOPE_PLUGINS, "Extensions/AutoTimer/locale"))

def _(txt):
	t = gettext.dgettext("AutoTimer", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)

try:
	xrange = xrange
	iteritems = lambda d: d.iteritems()
	itervalues = lambda d: d.itervalues()
except NameError:
	xrange = range
	iteritems = lambda d: d.items()
	itervalues = lambda d: d.values()

