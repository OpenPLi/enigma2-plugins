# for localized messages
from __init__ import _
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSubList, ConfigSelection
from Plugins.Plugin import PluginDescriptor
from enigma import iPlayableService, eTimer
from Screens import Standby
from Screens.Screen import Screen
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import SystemInfo
from AC3utils import AC3, PCM, AC3GLOB, PCMGLOB, AC3PCM
import NavigationInstance
import AC3setup
import os

config.plugins.AC3LipSync = ConfigSubsection()
config.plugins.AC3LipSync.outerBounds = ConfigInteger(default = 1000, limits = (-10000,10000))
config.plugins.AC3LipSync.arrowStepSize = ConfigInteger(default = 5, limits = (-10000,10000))
config.plugins.AC3LipSync.activationDelay = ConfigInteger(default = 800, limits = (-10000,10000))
config.plugins.AC3LipSync.stepSize13 = ConfigInteger(default = 50, limits = (-10000,10000))
config.plugins.AC3LipSync.stepSize46 = ConfigInteger(default = 200, limits = (-10000,10000))
config.plugins.AC3LipSync.stepSize79 = ConfigInteger(default = 500, limits = (-10000,10000))
config.plugins.AC3LipSync.absoluteStep2 = ConfigInteger(default = 0, limits = (-10000,10000))
config.plugins.AC3LipSync.absoluteStep5 = ConfigInteger(default = 0, limits = (-10000,10000))
config.plugins.AC3LipSync.absoluteStep8 = ConfigInteger(default = 0, limits = (-10000,10000))
config.plugins.AC3LipSync.position_x = ConfigInteger(default=0)
config.plugins.AC3LipSync.position_y = ConfigInteger(default=0)

config.plugins.AC3LipSync.restartSelection = ConfigSelection( default = "disabled", choices = [("disabled", _("disabled")), ("restart", _("after restart")), ("standby", _("after standby")), ("both", _("after restart/standby"))])
config.plugins.AC3LipSync.restartDelay = ConfigInteger(default = 10, limits = (0,30))

audio_restart = None
Session = None
audio_delay = None

CONFIG_FILE = '/etc/enigma2/audiosync.conf'

def getServiceDict():
	filename = {}
	if os.path.exists(CONFIG_FILE):
		try:
			cfg = open(CONFIG_FILE, 'r')
		except:
			return filename
		file = cfg.readlines()
		cfg.close()
		for line in file:
			line = line.split() 
			if len(line) == 2:
				filename[line[0]] = (line[0], line[1])
	return filename

def saveServiceDict(filename):
	try:
		cfg = open(CONFIG_FILE, 'w')
	except:
		return
	for ref, val in filename.items():
		cfg.write('%s %s\n' % (val[0], val[1]))
	cfg.close()

class AudioRestart():
	def __init__(self):
		self.activateTimer = eTimer()
		self.activateTimer.callback.append(self.restartAudio)
		if config.plugins.AC3LipSync.restartSelection.value in ["standby", "both"]:
			config.misc.standbyCounter.addNotifier(self.enterStandby, initial_call = False)
		if config.plugins.AC3LipSync.restartSelection.value in ["restart", "both"]:
			self.startTimer()

	def enterStandby(self,configElement):
		Standby.inStandby.onClose.append(self.endStandby)

	def removeNotifier(self):
		config.misc.standbyCounter.removeNotifier(self.enterStandby)

	def endStandby(self):
		self.startTimer()

	def startTimer(self):
		self.intDelay = config.plugins.AC3LipSync.restartDelay.value * 1000
		print "[AudioSync] audio restart in ",self.intDelay
		self.activateTimer.start(self.intDelay, True)

	def restartAudio(self):
		self.activateTimer.stop()
		if self.audioIsAC3() and SystemInfo["CanDownmixAC3"] and not config.av.downmix_ac3.value:
			config.av.downmix_ac3.value = True
			config.av.downmix_ac3.save()
			config.av.downmix_ac3.value = False
			config.av.downmix_ac3.save()
			print "[AudioSync] audio restarted"

	def audioIsAC3(self):
		service = NavigationInstance.instance and NavigationInstance.instance.getCurrentService()
		audioTracks = service and service.audioTracks()
		AC3 = False
		if audioTracks is not None:
			n = audioTracks and audioTracks.getNumberOfTracks() or 0
			if n >= 0:
				selectedAudioIndex = audioTracks.getCurrentTrack()
				if selectedAudioIndex <= n:
					trackInfo = audioTracks.getTrackInfo(selectedAudioIndex)
					description = trackInfo.getDescription()
					if (description.find("AC3") != -1 or description.find("AC-3") != -1) or description.find("DTS") != -1:
						AC3 = True
		return AC3

class audioDelay(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.newService = False
		self.ServiceDelay = getServiceDict()
		self.__event_tracker = ServiceEventTracker(screen = self, eventmap =
			{
				iPlayableService.evUpdatedInfo: self.__audiodelayUpdatedInfo,
				iPlayableService.evStart: self.__audiodelayStart,
				iPlayableService.evEnd: self.__audiodelayServiceEnd
			})

	def __audiodelayStart(self):
		self.newService = True

	def __audiodelayServiceEnd(self):
		self.newService = False

	def __audiodelayUpdatedInfo(self):
		if self.newService:
			self.newService = False
			iServiceReference = NavigationInstance.instance and NavigationInstance.instance.getCurrentlyPlayingServiceReference()
			isStreamService = iServiceReference and '%3a//' in iServiceReference.toCompareString()
			if isStreamService:
				delay_service = self.ServiceDelay.get(iServiceReference.toCompareString(), None)
				if delay_service:
					delay_value = int(delay_service[1])
					from AC3delay import AC3delay
					AC3delay = AC3delay()
					sAudio = AC3delay.whichAudio
					if sAudio == AC3 or sAudio == PCM:
						AC3delay.setSystemDelay(sAudio, delay_value, True)
						print "[AudioSync] set stream service audio delay %s" % delay_value

def autostart(reason, **kwargs):
	global audio_restart, Session, audio_delay
	if reason == 0 and "session" in kwargs:
		Session = kwargs["session"]
		if Session and audio_delay is None:
			audio_delay = audioDelay(Session)
		if config.plugins.AC3LipSync.restartSelection.value != "disabled" and audio_restart is None:
			audio_restart = AudioRestart()
	elif reason == 1:
		audio_delay = None
		if audio_restart:
			audio_restart.removeNotifier()
			audio_restart = None

def main(session, **kwargs):
	import AC3main
	session.open(AC3main.AC3LipSync, plugin_path)

def setup(session, **kwargs):
	session.open(AC3setup.AC3LipSyncSetup, plugin_path)

def audioMenu(session, **kwargs):
	import AC3main
	session.open(AC3main.AC3LipSync, plugin_path)

def Plugins(path,**kwargs):
	global plugin_path
	plugin_path = path
	return [ PluginDescriptor(name=_("Audio Sync Setup"), description=_("Setup for the Audio Sync Plugin"), icon = "AudioSync.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=setup),
		PluginDescriptor(name=_("Audio Sync"), description=_("sets the Audio Delay (LipSync)"), where = PluginDescriptor.WHERE_AUDIOMENU, fnc=audioMenu),
		PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc=autostart)]
