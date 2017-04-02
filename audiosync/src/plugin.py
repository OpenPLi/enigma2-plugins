# for localized messages
from __init__ import _
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSubList, ConfigSelection
from Plugins.Plugin import PluginDescriptor
from enigma import eTimer
from Screens import Standby
from Components.SystemInfo import SystemInfo
import NavigationInstance
import AC3main
import AC3setup

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

def sessionstart(reason, **kwargs):
	global audio_restart
	if reason == 0 and audio_restart is None:
		audio_restart = AudioRestart()

def main(session, **kwargs):
	session.open(AC3main.AC3LipSync, plugin_path)

def setup(session, **kwargs):
	session.open(AC3setup.AC3LipSyncSetup, plugin_path)

def audioMenu(session, **kwargs):
	session.open(AC3main.AC3LipSync, plugin_path)

def Plugins(path,**kwargs):
	global plugin_path
	plugin_path = path
	lst = [ PluginDescriptor(name=_("Audio Sync Setup"), description=_("Setup for the Audio Sync Plugin"), icon = "AudioSync.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=setup),
		PluginDescriptor(name=_("Audio Sync"), description=_("sets the Audio Delay (LipSync)"), where = PluginDescriptor.WHERE_AUDIOMENU, fnc=audioMenu)]
	if config.plugins.AC3LipSync.restartSelection.value != "disabled":
		lst.append(PluginDescriptor(name="Restart audio", where=PluginDescriptor.WHERE_SESSIONSTART, fnc = sessionstart))
	return lst
