from Components.Language import language
import os, gettext

"""RecInfobar"""

PLUGIN_PATH = os.path.dirname( __file__ )
PLUGIN_NAME = os.path.basename(PLUGIN_PATH)
TEXT_DOMAIN = PLUGIN_NAME

def localeInit():
	gettext.bindtextdomain(TEXT_DOMAIN, "%s/locale"%(PLUGIN_PATH))

def _(txt):
	t = gettext.dgettext(TEXT_DOMAIN, txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

def _N(singular, plural, n):
	t = gettext.dngettext(TEXT_DOMAIN, singular, plural, n)
	if t in (singular, plural):
		t = gettext.ngettext(singular, plural, n)
	return t

localeInit()
language.addCallback(localeInit)
