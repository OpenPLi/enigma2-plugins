AC_INIT([enigma2-plugins],[4],[forum@openpli.org])
AM_INIT_AUTOMAKE([dist-bzip2 foreign no-define tar-pax])

# Silent rules are available since 1.11, but older versions
# are still in use. So don't use them unconditionally.
m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES([yes])])

AC_SYS_LARGEFILE

AC_PATH_PROG(MSGFMT, msgfmt, AC_MSG_ERROR(Could not find msgfmt))

AM_PATH_PYTHON

AC_ARG_WITH(debug,
	AS_HELP_STRING([--without-debug],[disable debugging code]),
	[with_debug="$withval"],[with_debug="yes"])
if test "$with_debug" = "yes"; then
	AC_DEFINE([DEBUG],[1],[Define to 1 to enable debugging code])
fi

AC_ARG_WITH(po,
	AS_HELP_STRING([--with-po],[enable updating of po files]),
	[with_po="$withval"],[with_po="no"])
if test "$with_po" = "yes"; then
	AC_PATH_PROG(MSGINIT, msginit)
	AC_PATH_PROG(MSGMERGE, msgmerge)
	AC_PATH_PROG(MSGUNIQ, msguniq)
	AC_PATH_PROG(MSGATTRIB, msgattrib)
	AC_PATH_PROG(XGETTEXT, xgettext)
	if test -z "$MSGINIT" -o -z "$MSGMERGE" -o -z "$MSGUNIQ" -o -z "$MSGATTRIB" -o -z "$XGETTEXT"; then
		AC_MSG_ERROR([Could not find required gettext tools])
	fi
fi
AM_CONDITIONAL(UPDATE_PO, test "$with_po" = "yes")

AC_CONFIG_FILES([
Makefile

aihdcontroler/Makefile
aihdcontroler/meta/Makefile
aihdcontroler/src/Makefile
aihdcontroler/src/comp/Makefile
aihdcontroler/src/data/Makefile

antiscrollbar/Makefile
antiscrollbar/meta/Makefile
antiscrollbar/src/Makefile

ardmediathek/Makefile
ardmediathek/meta/Makefile
ardmediathek/src/Makefile
ardmediathek/src/img/Makefile

audiosync/Makefile
audiosync/img/Makefile
audiosync/meta/Makefile
audiosync/po/Makefile
audiosync/src/Makefile

automaticcleanup/Makefile
automaticcleanup/meta/Makefile
automaticcleanup/po/Makefile
automaticcleanup/src/Makefile

automaticvolumeadjustment/Makefile
automaticvolumeadjustment/meta/Makefile
automaticvolumeadjustment/src/Makefile
automaticvolumeadjustment/po/Makefile

autoresolution/Makefile
autoresolution/meta/Makefile
autoresolution/src/Makefile
autoresolution/po/Makefile

autotimer/Makefile
autotimer/po/Makefile
autotimer/meta/Makefile
autotimer/src/WebComponents/Makefile
autotimer/src/WebScreens/Makefile
autotimer/src/Makefile
autotimer/src/web-data/Makefile
autotimer/src/WebChilds/Makefile
autotimer/src/web/Makefile

babelzapper/Makefile
babelzapper/etc/Makefile
babelzapper/meta/Makefile
babelzapper/src/Makefile

blindscan/src/Makefile
blindscan/po/Makefile
blindscan/Makefile
blindscan/meta/Makefile
blindscan/src/images/Makefile

bonjour/Makefile
bonjour/meta/Makefile
bonjour/src/Makefile

cdinfo/Makefile
cdinfo/meta/Makefile
cdinfo/src/Makefile

dreamexplorer/Makefile
dreamexplorer/meta/Makefile
dreamexplorer/po/Makefile
dreamexplorer/src/Makefile
dreamexplorer/src/res/Makefile

dreamirc/Makefile
dreamirc/meta/Makefile
dreamirc/src/Makefile
dreamirc/src/protocols/Makefile

dreammediathek/Makefile
dreammediathek/src/Makefile

dvdbackup/Makefile
dvdbackup/src/Makefile
dvdbackup/po/Makefile
dvdbackup/meta/Makefile

dyndns/Makefile
dyndns/src/Makefile
dyndns/meta/Makefile

easyinfo/Makefile
easyinfo/meta/Makefile
easyinfo/src/Makefile

easymedia/Makefile
easymedia/meta/Makefile
easymedia/po/Makefile
easymedia/src/Makefile

eibox/Makefile
eibox/meta/Makefile
eibox/po/Makefile
eibox/src/Makefile
eibox/src/images/Makefile

emailclient/Makefile
emailclient/meta/Makefile
emailclient/po/Makefile
emailclient/src/Makefile

epgrefresh/Makefile
epgrefresh/meta/Makefile
epgrefresh/po/Makefile
epgrefresh/src/Makefile
epgrefresh/src/webinterface/Makefile

epgsearch/Makefile
epgsearch/meta/Makefile
epgsearch/po/Makefile
epgsearch/src/Makefile
epgsearch/src/icons/Makefile

fancontrol2/Makefile
fancontrol2/meta/Makefile
fancontrol2/po/Makefile
fancontrol2/src/Makefile
fancontrol2/src/data/Makefile

filebrowser/Makefile
filebrowser/meta/Makefile
filebrowser/src/Makefile
filebrowser/po/Makefile

fstabeditor/Makefile
fstabeditor/meta/Makefile
fstabeditor/src/Makefile

ftpbrowser/Makefile
ftpbrowser/meta/Makefile
ftpbrowser/po/Makefile
ftpbrowser/src/Makefile
ftpbrowser/src/images/Makefile

growlee/Makefile
growlee/meta/Makefile
growlee/src/Makefile

httpproxy/Makefile
httpproxy/meta/Makefile
httpproxy/src/Makefile

imdb/Makefile
imdb/meta/Makefile
imdb/po/Makefile
imdb/src/Makefile

kiddytimer/Makefile
kiddytimer/img/Makefile
kiddytimer/meta/Makefile
kiddytimer/po/Makefile
kiddytimer/src/Makefile

letterbox/Makefile
letterbox/src/Makefile
letterbox/meta/Makefile

logomanager/Makefile
logomanager/meta/Makefile
logomanager/po/Makefile
logomanager/src/Makefile

mediadownloader/Makefile
mediadownloader/meta/Makefile
mediadownloader/po/Makefile
mediadownloader/src/Makefile

mediathekviewweb/Makefile
mediathekviewweb/meta/Makefile
mediathekviewweb/src/Makefile
mediathekviewweb/src/img/Makefile

merlinepg/Makefile
merlinepg/meta/Makefile
merlinepg/src/Makefile

merlinepgcenter/Makefile
merlinepgcenter/meta/Makefile
merlinepgcenter/src/Makefile
merlinepgcenter/po/Makefile
merlinepgcenter/skins/Makefile
merlinepgcenter/images/Makefile
merlinepgcenter/images/HD/Makefile
merlinepgcenter/images/HD_BORDER/Makefile
merlinepgcenter/images/SD/Makefile
merlinepgcenter/images/XD/Makefile
merlinepgcenter/images/XD_BORDER/Makefile

merlinmusicplayer/Makefile
merlinmusicplayer/meta/Makefile
merlinmusicplayer/po/Makefile
merlinmusicplayer/src/Makefile
merlinmusicplayer/src/images/Makefile

mosaic/Makefile
mosaic/meta/Makefile
mosaic/po/Makefile
mosaic/src/Makefile

movieretitle/Makefile
movieretitle/meta/Makefile
movieretitle/po/Makefile
movieretitle/src/Makefile

movietagger/Makefile
movietagger/etc/Makefile
movietagger/meta/Makefile
movietagger/po/Makefile
movietagger/src/Makefile

mphelp/Makefile
mphelp/meta/Makefile
mphelp/src/Makefile

multirc/Makefile
multirc/src/Makefile
multirc/meta/Makefile

netcaster/Makefile
netcaster/meta/Makefile
netcaster/src/Makefile
netcaster/src/bin/Makefile
netcaster/src/bin/interface/Makefile
netcaster/src/etc/Makefile

netzkino/Makefile
netzkino/meta/Makefile
netzkino/src/Makefile

ncidclient/Makefile
ncidclient/meta/Makefile
ncidclient/po/Makefile
ncidclient/src/Makefile

ofdb/Makefile
ofdb/meta/Makefile
ofdb/po/Makefile
ofdb/src/Makefile

orfat/Makefile
orfat/meta/Makefile
orfat/src/Makefile

orfteletext/Makefile
orfteletext/meta/Makefile
orfteletext/src/Makefile

partnerbox/Makefile
partnerbox/meta/Makefile
partnerbox/po/Makefile
partnerbox/src/Makefile
partnerbox/src/icons/Makefile

permanentclock/Makefile
permanentclock/meta/Makefile
permanentclock/po/Makefile
permanentclock/src/Makefile
permanentclock/src/trad/Makefile

pluginhider/Makefile
pluginhider/meta/Makefile
pluginhider/po/Makefile
pluginhider/src/Makefile

porncenter/Makefile
porncenter/meta/Makefile
porncenter/po/Makefile
porncenter/src/Makefile
porncenter/src/Additions/Makefile

primetimemanager/Makefile
primetimemanager/meta/Makefile
primetimemanager/po/Makefile
primetimemanager/src/Makefile
primetimemanager/src/images/Makefile

reconstructapsc/Makefile
reconstructapsc/meta/Makefile
reconstructapsc/src_py/Makefile
reconstructapsc/po/Makefile

remotetimer/Makefile
remotetimer/meta/Makefile
remotetimer/po/Makefile
remotetimer/src/Makefile

recordinfobar/Makefile
recordinfobar/meta/Makefile
recordinfobar/po/Makefile
recordinfobar/src/Makefile

satipclient/Makefile
satipclient/meta/Makefile
satipclient/po/Makefile
satipclient/src/Makefile

seekbar/Makefile
seekbar/meta/Makefile
seekbar/po/Makefile
seekbar/src/Makefile

setpasswd/Makefile
setpasswd/meta/Makefile
setpasswd/po/Makefile
setpasswd/src/Makefile

shoutcast/Makefile
shoutcast/meta/Makefile
shoutcast/po/Makefile
shoutcast/src/Makefile

showclock/Makefile
showclock/meta/Makefile
showclock/po/Makefile
showclock/src/Makefile

simplerss/Makefile
simplerss/meta/Makefile
simplerss/po/Makefile
simplerss/src/Makefile

srfmediathek/Makefile
srfmediathek/meta/Makefile
srfmediathek/src/Makefile
srfmediathek/src/img/Makefile

systemtime/Makefile
systemtime/meta/Makefile
systemtime/po/Makefile
systemtime/src/Makefile
systemtime/src/images/Makefile

svdrp/Makefile
svdrp/meta/Makefile
svdrp/src/Makefile

tageditor/Makefile
tageditor/meta/Makefile
tageditor/po/Makefile
tageditor/src/Makefile

trafficinfo/Makefile
trafficinfo/meta/Makefile
trafficinfo/src/Makefile

transcodingsetup/Makefile
transcodingsetup/src/Makefile
transcodingsetup/po/Makefile
transcodingsetup/meta/Makefile

transmission/Makefile
transmission/src/Makefile
transmission/po/Makefile
transmission/meta/Makefile

tvcharts/Makefile
tvcharts/meta/Makefile
tvcharts/src/Makefile

unwetterinfo/Makefile
unwetterinfo/meta/Makefile
unwetterinfo/src/Makefile

valixdcontrol/Makefile
valixdcontrol/meta/Makefile
valixdcontrol/src/Makefile
valixdcontrol/src/comp/Makefile
valixdcontrol/src/data/Makefile

virtualzap/Makefile
virtualzap/meta/Makefile
virtualzap/po/Makefile
virtualzap/src/Makefile

vlcplayer/Makefile
vlcplayer/meta/Makefile
vlcplayer/po/Makefile
vlcplayer/src/Makefile

vfdcontrol/Makefile
vfdcontrol/meta/Makefile
vfdcontrol/po/Makefile
vfdcontrol/src/Makefile

webcamviewer/Makefile
webcamviewer/meta/Makefile
webcamviewer/src/Makefile

werbezapper/Makefile
werbezapper/meta/Makefile
werbezapper/po/Makefile
werbezapper/src/Makefile

zaphistorybrowser/Makefile
zaphistorybrowser/meta/Makefile
zaphistorybrowser/po/Makefile
zaphistorybrowser/src/Makefile

zapstatistic/Makefile
zapstatistic/meta/Makefile
zapstatistic/po/Makefile
zapstatistic/src/Makefile

zdfmediathek/Makefile
zdfmediathek/meta/Makefile
zdfmediathek/src/Makefile
zdfmediathek/src/img/Makefile

])
AC_OUTPUT
