from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import gettext

PluginLanguageDomain = "IMDb"
PluginLanguagePath = "Extensions/IMDb/locale"


def localeInit():
	gettext.bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))


def _(txt):
	t = gettext.dgettext(PluginLanguageDomain, txt)
	if t == txt:
		# print("[%s] fallback to default translation for %s" % (PluginLanguageDomain, txt))
		t = gettext.gettext(txt)
	return t


def ngettext(singular, plural, n):
	t = gettext.dngettext(PluginLanguageDomain, singular, plural, n)
	if t in (singular, plural):
		# print("[%s] fallback to default translation for %s, %s, %d" % (PluginLanguageDomain, singular, plural, n))
		t = gettext.ngettext(singular, plural, n)
	return t


localeInit()
language.addCallback(localeInit)

__version__ = "1.2"
