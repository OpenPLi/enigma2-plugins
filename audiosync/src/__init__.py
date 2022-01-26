import gettext

from Components.Language import language
from Tools.Directories import SCOPE_PLUGINS, resolveFilename

PluginLanguageDomain = "AudioSync"
PluginLanguagePath = "Extensions/AudioSync/locale"


def localeInit():
	gettext.bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))


def _(txt):
	t = gettext.dgettext(PluginLanguageDomain, txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t


localeInit()
language.addCallback(localeInit)
