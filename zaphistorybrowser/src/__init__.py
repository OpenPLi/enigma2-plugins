from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import gettext


def localeInit():
	gettext.bindtextdomain("ZapHistoryBrowser", resolveFilename(SCOPE_PLUGINS, "Extensions/ZapHistoryBrowser/locale"))


def _(txt):
	t = gettext.dgettext("ZapHistoryBrowser", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t


localeInit()
language.addCallback(localeInit)
