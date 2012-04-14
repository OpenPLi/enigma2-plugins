# -*- coding: ISO-8859-1 -*-
#===============================================================================
# YouTube Plugin by Volker Christian 2008
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2, or (at your option) any later
# version.
#===============================================================================

from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
import os,gettext

def localeInit():
    gettext.bindtextdomain("YouTubePlayer", resolveFilename(SCOPE_PLUGINS, "Extensions/YouTubePlayer/locale"))

def _(txt):
    t = gettext.dgettext("YouTubePlayer", txt)
    if t == txt:
        print "[YTB] fallback to default translation for", txt
        t = gettext.gettext(txt)
    return t

localeInit()
