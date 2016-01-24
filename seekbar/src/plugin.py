##
## Seekbar
## by AliAbdul

from Components.ActionMap import ActionMap
from Components.config import config, ConfigInteger, ConfigNumber, ConfigSelection, ConfigSubsection, ConfigYesNo, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Language import language
from Components.Pixmap import MovingPixmap
from enigma import eTimer
from keyids import KEYIDS
from os import environ
from Screens.Screen import Screen
from Screens.InfoBar import MoviePlayer, InfoBar
from Tools.Directories import fileExists, resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS
from Tools.KeyBindings import addKeyBinding
import gettext, keymapparser

##############################################

config.plugins.Seekbar = ConfigSubsection()
config.plugins.Seekbar.overwrite_left_right = ConfigYesNo(default=True)
config.plugins.Seekbar.sensibility = ConfigInteger(default=10, limits=(1, 10))

##############################################

def localeInit():
	gettext.bindtextdomain("Seekbar", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "Extensions/Seekbar/locale/"))

localeInit()
language.addCallback(localeInit)

def _(txt):
	t = gettext.dgettext("Seekbar", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

##############################################

class Seekbar(ConfigListScreen, Screen):
	skin = """
	<screen position="center,center" size="560,160" title="%s">
		<widget name="config" position="10,10" size="540,100" scrollbarMode="showOnDemand" />
		<widget name="cursor" position="0,125" size="8,18" pixmap="skin_default/position_arrow.png" alphatest="on" />
		<widget source="session.CurrentService" render="PositionGauge" position="145,140" size="270,10" zPosition="2" pointer="skin_default/position_pointer.png:540,0" transparent="1" foregroundColor="#20224f">
			<convert type="ServicePosition">Gauge</convert>
		</widget>
		<widget name="time" position="50,130" size="100,20" font="Regular;20" halign="left" backgroundColor="#4e5a74" transparent="1" />
		<widget source="session.CurrentService" render="Label" position="420,130" size="90,24" font="Regular;20" halign="right" backgroundColor="#4e5a74" transparent="1">
			<convert type="ServicePosition">Length</convert>
		</widget>
	</screen>""" % _("Seek")

	def __init__(self, session, instance, fwd):
		Screen.__init__(self, session)
		
		self.session = session
		self.infobarInstance = instance
		self.fwd = fwd
		self.movie = isinstance(session.current_dialog, MoviePlayer)
		try:
			self.media_player = isinstance(session.current_dialog, MediaPlayer)
		except:
			self.media_player = False
		try:
			self.dvd_pli = isinstance(session.current_dialog, DVDPlayer)
		except:
			self.dvd_pli = False
		try:
			self.old_dvd = isinstance(session.current_dialog, DVDPlayer2)
		except:
			self.old_dvd = False
		try:
			self.ytube = isinstance(session.current_dialog, YouTubePlayer)
		except:
			self.ytube = False
		try:
			self.tmbd_trailer = isinstance(session.current_dialog, tmbdTrailerPlayer)
		except:
			self.tmbd_trailer = False
		try:
			self.vod = isinstance(session.current_dialog, nVODplayer)
		except:
			self.vod = False
		try:
			self.yamp_player = isinstance(session.current_dialog, YampScreen)
		except:
			self.yamp_player = False
		try:
			self.seasondream = isinstance(session.current_dialog, Player)
		except:
			self.seasondream = False
		try:
			self.timeshift = isinstance(session.current_dialog, InfoBar)
		except:
			self.timeshift = False
		self.percent = 0.0
		self.length = None
		service = session.nav.getCurrentService()
		if service:
			self.seek = service.seek()
			if self.seek:
				self.length = self.seek.getLength()
				position = self.seek.getPlayPosition()
				if self.length and position:
					if int(position[1]) > 0:
						self.percent = float(position[1]) * 100.0 / float(self.length[1])
		
		self.minuteInput = ConfigNumber(default=5)
		self.positionEntry = ConfigSelection(choices=["<>"], default="<>")
		if self.fwd:
			txt = _("Jump x minutes forward:")
		else:
			txt = _("Jump x minutes back:")
		ConfigListScreen.__init__(self, [
			getConfigListEntry(txt, self.minuteInput),
			getConfigListEntry(_("Go to position:"), self.positionEntry),
			getConfigListEntry(_("Sensibility:"), config.plugins.Seekbar.sensibility),
			getConfigListEntry(_("Overwrite left and right buttons:"), config.plugins.Seekbar.overwrite_left_right)])
		
		self["cursor"] = MovingPixmap()
		self["time"] = Label()
		
		self["actions"] = ActionMap(["WizardActions"], {"back": self.exit}, -1)
		
		self.cursorTimer = eTimer()
		self.cursorTimer.callback.append(self.updateCursor)
		self.cursorTimer.start(200, False)
		
		self.onLayoutFinish.append(self.firstStart)

	def firstStart(self):
		self["config"].setCurrentIndex(1)

	def updateCursor(self):
		if self.length:
			x = 145 + int(2.7 * self.percent)
			self["cursor"].moveTo(x, 125, 1)
			self["cursor"].startMoving()
			pts = int(float(self.length[1]) / 100.0 * self.percent)
			self["time"].setText("%d:%02d" % ((pts/60/90000), ((pts/90000)%60)))

	def exit(self):
		self.cursorTimer.stop()
		ConfigListScreen.saveAll(self)
		self.close()

	def keyOK(self):
		sel = self["config"].getCurrent()[1]
		if sel == self.positionEntry:
			if self.length:
				if self.old_dvd: # seekTo() doesn't work for DVD Player
					oldPosition = self.seek.getPlayPosition()[1]
					newPosition = int(float(self.length[1]) / 100.0 * self.percent)
					if newPosition > oldPosition:
						pts = newPosition - oldPosition
					else:
						pts = -1*(oldPosition - newPosition)
					DVDPlayer2.doSeekRelative(self.infobarInstance, pts)
				elif self.media_player:
					oldPosition = self.seek.getPlayPosition()[1]
					newPosition = int(float(self.length[1]) / 100.0 * self.percent)
					if newPosition > oldPosition:
						pts = newPosition - oldPosition
					else:
						pts = -1 * (oldPosition - newPosition)
					MediaPlayer.doSeekRelative(self.infobarInstance, pts)
				elif self.dvd_pli:
					oldPosition = self.seek.getPlayPosition()[1]
					newPosition = int(float(self.length[1]) / 100.0 * self.percent)
					if newPosition > oldPosition:
						pts = newPosition - oldPosition
					else:
						pts = -1 * (oldPosition - newPosition)
					DVDPlayer.doSeekRelative(self.infobarInstance, pts)
				elif self.ytube:
					oldPosition = self.seek.getPlayPosition()[1]
					newPosition = int(float(self.length[1]) / 100.0 * self.percent)
					if newPosition > oldPosition:
						pts = newPosition - oldPosition
					else:
						pts = -1 * (oldPosition - newPosition)
					YouTubePlayer.doSeekRelative(self.infobarInstance, pts)
				elif self.tmbd_trailer:
					oldPosition = self.seek.getPlayPosition()[1]
					newPosition = int(float(self.length[1]) / 100.0 * self.percent)
					if newPosition > oldPosition:
						pts = newPosition - oldPosition
					else:
						pts = -1 * (oldPosition - newPosition)
					tmbdTrailerPlayer.doSeekRelative(self.infobarInstance, pts)
				elif self.vod:
					oldPosition = self.seek.getPlayPosition()[1]
					newPosition = int(float(self.length[1]) / 100.0 * self.percent)
					if newPosition > oldPosition:
						pts = newPosition - oldPosition
					else:
						pts = -1 * (oldPosition - newPosition)
					nVODplayer.doSeekRelative(self.infobarInstance, pts)
				elif self.yamp_player:
					oldPosition = self.seek.getPlayPosition()[1]
					newPosition = int(float(self.length[1]) / 100.0 * self.percent)
					if newPosition > oldPosition:
						pts = newPosition - oldPosition
					else:
						pts = -1 * (oldPosition - newPosition)
					YampScreen.doSeekRelative(self.infobarInstance, pts)
				elif self.seasondream:
					oldPosition = self.seek.getPlayPosition()[1]
					newPosition = int(float(self.length[1]) / 100.0 * self.percent)
					if newPosition > oldPosition:
						pts = newPosition - oldPosition
					else:
						pts = -1 * (oldPosition - newPosition)
					Player.doSeekRelative(self.infobarInstance, pts)
				elif self.movie:
					self.seek.seekTo(int(float(self.length[1]) / 100.0 * self.percent))
				elif self.timeshift:
					self.seek.seekTo(int(float(self.length[1]) / 100.0 * self.percent))
				else:
					pass
				self.exit()
		elif sel == self.minuteInput:
			pts = self.minuteInput.value * 60 * 90000
			if self.fwd == False:
				pts = -1*pts
			if self.old_dvd:
				DVDPlayer2.doSeekRelative(self.infobarInstance, pts)
			elif self.media_player:
				MediaPlayer.doSeekRelative(self.infobarInstance, pts)
			elif self.dvd_pli:
				DVDPlayer.doSeekRelative(self.infobarInstance, pts)
			elif self.ytube:
				YouTubePlayer.doSeekRelative(self.infobarInstance, pts)
			elif self.tmbd_trailer:
				tmbdTrailerPlayer.doSeekRelative(self.infobarInstance, pts)
			elif self.vod:
				nVODplayer.doSeekRelative(self.infobarInstance, pts)
			elif self.yamp_player:
				YampScreen.doSeekRelative(self.infobarInstance, pts)
			elif self.seasondream:
				Player.doSeekRelative(self.infobarInstance, pts)
			elif self.movie:
				MoviePlayer.doSeekRelative(self.infobarInstance, pts)
			elif self.timeshift:
				InfoBar.doSeekRelative(self.infobarInstance, pts)
			else:
				pass
			self.exit()

	def keyLeft(self):
		sel = self["config"].getCurrent()[1]
		if sel == self.positionEntry:
			self.percent -= float(config.plugins.Seekbar.sensibility.value) / 10.0
			if self.percent < 0.0:
				self.percent = 0.0
		else:
			ConfigListScreen.keyLeft(self)

	def keyRight(self):
		sel = self["config"].getCurrent()[1]
		if sel == self.positionEntry:
			self.percent += float(config.plugins.Seekbar.sensibility.value) / 10.0
			if self.percent > 100.0:
				self.percent = 100.0
		else:
			ConfigListScreen.keyRight(self)

	def keyNumberGlobal(self, number):
		sel = self["config"].getCurrent()[1]
		if sel == self.positionEntry:
			self.percent = float(number) * 10.0
		else:
			ConfigListScreen.keyNumberGlobal(self, number)

##############################################
# This hack overwrites the functions seekFwdManual and seekBackManual of the InfoBarSeek class (MoviePlayer and DVDPlayer)

def seekbar(instance, fwd=True):
	if instance and instance.session:
		instance.session.open(Seekbar, instance, fwd)

def seekbarBack(instance):
	seekbar(instance, False)

MoviePlayer.seekFwdManual = seekbar
MoviePlayer.seekBackManual = seekbarBack
InfoBar.seekFwdManual = seekbar
InfoBar.seekBackManual = seekbarBack
if fileExists("/usr/lib/enigma2/python/Screens/DVD.pyo"):
	try:
		from Screens.DVD import DVDPlayer
	except:
		pass
	else:
		DVDPlayer.seekFwdManual = seekbar
		DVDPlayer.seekBackManual = seekbarBack

dvdPlayer = "%s%s" % (resolveFilename(SCOPE_PLUGINS), "Extensions/DVDPlayer/plugin.pyo")
dvdPlayerKeymap = "%s%s" % (resolveFilename(SCOPE_PLUGINS), "Extensions/DVDPlayer/keymap.xml")
if fileExists(dvdPlayer) and fileExists(dvdPlayerKeymap):
	try:
		from Plugins.Extensions.DVDPlayer.plugin import DVDPlayer as DVDPlayer2
	except:
		pass
	else:
		DVDPlayer2.seekFwdManual = seekbar
		DVDPlayer2.seekBackManual = seekbarBack
mediaplayer = '%s%s' % (resolveFilename(SCOPE_PLUGINS), 'Extensions/MediaPlayer/plugin.pyo')
if fileExists(mediaplayer):
	try:
		from Plugins.Extensions.MediaPlayer.plugin import MediaPlayer
	except:
		pass
	else:
		MediaPlayer.seekFwdManual = seekbar
		MediaPlayer.seekBackManual = seekbarBack
youTubePlayer = '%s%s' % (resolveFilename(SCOPE_PLUGINS), 'Extensions/YouTube/plugin.pyo')
youTubePlayerUi = '%s%s' % (resolveFilename(SCOPE_PLUGINS), 'Extensions/YouTube/YouTubeUi.pyo')
if fileExists(youTubePlayer) and fileExists(youTubePlayerUi):
	try:
		from Plugins.Extensions.YouTube.YouTubeUi import YouTubePlayer
	except:
		pass
	else:
		YouTubePlayer.seekFwdManual = seekbar
		YouTubePlayer.seekBackManual = seekbarBack
tmbd = '%s%s' % (resolveFilename(SCOPE_PLUGINS), 'Extensions/TMBD/plugin.pyo')
if fileExists(tmbd):
	try:
		from Plugins.Extensions.TMBD.tmbdYTTrailer import tmbdTrailerPlayer
	except:
		pass
	else:
		tmbdTrailerPlayer.seekFwdManual = seekbar
		tmbdTrailerPlayer.seekBackManual = seekbarBack
nStreamVODPlayer = '%s%s' % (resolveFilename(SCOPE_PLUGINS), 'Extensions/nStreamVOD/plugin.pyo')
if fileExists(nStreamVODPlayer):
	try:
		from Plugins.Extensions.nStreamVOD.plugin import nVODplayer
	except:
		pass
	else:
		nVODplayer.seekFwdManual = seekbar
		nVODplayer.seekBackManual = seekbarBack
yampMusicPlayer = '%s%s' % (resolveFilename(SCOPE_PLUGINS), 'Extensions/YampMusicPlayer/plugin.pyo')
if fileExists(yampMusicPlayer):
	try:
		from Plugins.Extensions.YampMusicPlayer.Yamp import YampScreen
	except:
		pass
	else:
		YampScreen.seekFwdManual = seekbar
		YampScreen.seekBackManual = seekbarBack
seasondreamPlayer = '%s%s' % (resolveFilename(SCOPE_PLUGINS), 'Extensions/Seasondream/plugin.pyo')
if fileExists(seasondreamPlayer):
	try:
		from Plugins.Extensions.Seasondream.Player import Player
	except:
		pass
	else:
		Player.seekFwdManual = seekbar
		Player.seekBackManual = seekbarBack

##############################################
# This hack puts the functions seekFwdManual and seekBackManual to the maped keys to seekbarRight and seekbarLeft

DoBind = ActionMap.doBind
def doBind(instance):
	if not instance.bound:
		for ctx in instance.contexts:
			if ctx == "InfobarSeekActions":
				if instance.actions.has_key("seekFwdManual"):
					instance.actions["seekbarRight"] = instance.actions["seekFwdManual"]
				if instance.actions.has_key("seekBackManual"):
					instance.actions["seekbarLeft"] = instance.actions["seekBackManual"]
			DoBind(instance)

if config.plugins.Seekbar.overwrite_left_right.value:
	ActionMap.doBind = doBind

##############################################
# This hack maps the keys left and right to seekbarRight and seekbarLeft in the InfobarSeekActions-context

KeymapError = keymapparser.KeymapError
ParseKeys = keymapparser.parseKeys
def parseKeys(context, filename, actionmap, device, keys):
	if context == "InfobarSeekActions":
		if device == "generic":
			for x in keys.findall("key"):
				get_attr = x.attrib.get
				mapto = get_attr("mapto")
				id = get_attr("id")
				if id == "KEY_LEFT":
					mapto = "seekbarLeft"
				if id == "KEY_RIGHT":
					mapto = "seekbarRight"
				flags = get_attr("flags")
				flag_ascii_to_id = lambda x: {'m':1,'b':2,'r':4,'l':8}[x]
				flags = sum(map(flag_ascii_to_id, flags))
				assert mapto, "%s: must specify mapto in context %s, id '%s'" % (filename, context, id)
				assert id, "%s: must specify id in context %s, mapto '%s'" % (filename, context, mapto)
				assert flags, "%s: must specify at least one flag in context %s, id '%s'" % (filename, context, id)
				if len(id) == 1:
					keyid = ord(id) | 0x8000
				elif id[0] == '\\':
					if id[1] == 'x':
						keyid = int(id[2:], 0x10) | 0x8000
					elif id[1] == 'd':
						keyid = int(id[2:]) | 0x8000
					else:
						raise KeymapError("key id '" + str(id) + "' is neither hex nor dec")
				else:
					try:
						keyid = KEYIDS[id]
					except:
						raise KeymapError("key id '" + str(id) + "' is illegal")
				actionmap.bindKey(filename, device, keyid, flags, context, mapto)
				addKeyBinding(filename, keyid, context, mapto, flags)
		else:
			ParseKeys(context, filename, actionmap, device, keys)
	else:
		ParseKeys(context, filename, actionmap, device, keys)

if config.plugins.Seekbar.overwrite_left_right.value:
	keymapparser.parseKeys = parseKeys
	keymapparser.removeKeymap(config.usage.keymap.value)
	keymapparser.readKeymap(config.usage.keymap.value)

##############################################

def Plugins(**kwargs):
	return []
