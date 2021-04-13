# -*- coding: utf-8 -*-
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE #@UnresolvedImport
import gettext
import os
import re
from enigma import eBackgroundFileEraser


def localeInit():
	gettext.bindtextdomain("NcidClient", resolveFilename(SCOPE_PLUGINS, "Extensions/NcidClient/locale/"))


localeInit()
language.addCallback(localeInit)


def _(txt): # pylint: disable-msg=C0103
	td = gettext.dgettext("NcidClient", txt)
	if td == txt:
		print "[NcidClient] fallback to default translation for", txt
		td = gettext.gettext(txt)

	return td


def debug(message):
	print message
