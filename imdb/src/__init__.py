from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import gettext

PluginLanguageDomain = "IMDb"
PluginLanguagePath = "Extensions/IMDb/locale"


def localeInit():
	gettext.bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))


def _(txt):
	if gettext.dgettext(PluginLanguageDomain, txt):
		return gettext.dgettext(PluginLanguageDomain, txt)
	else:
		return gettext.gettext(txt)

def ngettext(singular, plural, n):
	t = gettext.dngettext(PluginLanguageDomain, singular, plural, n)
	if t in (singular, plural):
		# print("[%s] fallback to default translation for %s, %s, %d" % (PluginLanguageDomain, singular, plural, n))
		t = gettext.ngettext(singular, plural, n)
	return t


localeInit()
language.addCallback(localeInit)

__version__ = "1.2"
