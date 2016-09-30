# -*- coding: utf-8 -*-
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import gettext

PluginLanguageDomain = "TerrestrialScan"
PluginLanguagePath = "SystemPlugins/TerrestrialScan/locale"

def localeInit():
	localedir = resolveFilename(SCOPE_PLUGINS, PluginLanguagePath)
	gettext.bindtextdomain(PluginLanguageDomain, localedir)

def _(txt):
	t = gettext.dgettext(PluginLanguageDomain, txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

language.addCallback(localeInit())
