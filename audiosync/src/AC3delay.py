import NavigationInstance
from Components.config import config
from enigma import eTimer
from Tools.HardwareInfo import HardwareInfo
from Tools.ISO639 import LanguageCodes

from . import _
from .AC3utils import AC3, AC3GLOB, AC3PCM, PCM


class AC3delay:
	def __init__(self):
		self.iService = None
		self.iServiceReference = None
		self.isStreamService = False
		self.iAudioDelay = None
		self.channelAudio = AC3
		self.whichAudio = AC3
		self.bIsRecording = False

		# Current audio- delay
		self.systemDelay = {}
		self.selectedAudioInfo = None
		self.getAudioInformation()

		self.activateTimer = eTimer()
		self.activateTimer.callback.append(self.activateDelay)
		self.activateWait = config.plugins.AC3LipSync.activationDelay.getValue()

		# Current value for movie start behaviour
		self.movieStart = config.usage.on_movie_start.getValue()

		# find out box type
		self.oHWInfo = HardwareInfo()
		self.bHasToRestartService = self.oHWInfo.get_device_name() == "dm7025"

	def initAudio(self):
		self.iService = NavigationInstance.instance.getCurrentService()
		self.iServiceReference = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		self.isStreamService = self.iServiceReference and '%3a//' in self.iServiceReference.toString()
		self.iAudioDelay = self.iService and self.iService.audioDelay()
		self.iSeek = self.iService and self.iService.seek()

	def deleteAudio(self):
		self.iService = None
		self.iAudioDelay = None
		self.iSeek = None

	def setChannelAudio(self, sAudio):
		self.channelAudio = sAudio

	def delayedActivateDelay(self):
		if self.activateTimer.isActive:
			self.activateTimer.stop()
		self.activateTimer.start(self.activateWait, True)

	def activateDelay(self):
		# This activation code is only neccessary for DM7025.
		# DM800, DM8000 and DM500HD directly activate the delay after using "setAC3Delay" and "setPCMDelay", they don't need the service restart
		if self.activateTimer.isActive:
			self.activateTimer.stop()
		if self.bHasToRestartService == True:
			if self.iService is None:
				self.initAudio()
			if self.iServiceReference is not None:
				lCurPosition = self.cueGetCurrentPosition()
				self.deleteAudio()
				if self.whichAudio == self.channelAudio:
					config.usage.on_movie_start.setValue("beginning")
					NavigationInstance.instance.stopService()
					NavigationInstance.instance.playService(self.iServiceReference)
					config.usage.on_movie_start.setValue(self.movieStart)
					if lCurPosition is not None:
						self.lCurPosition = lCurPosition
						self.timer = eTimer()
						self.timer.callback.append(self.seekAfterWait)
						self.timer.start(200, True)
			else:
				self.deleteAudio()

	def seekAfterWait(self):
		self.timer.stop()
		self.initAudio()
		if self.iSeek is not None:
			self.iSeek.seekTo(self.lCurPosition)
		self.deleteAudio()

	def cueGetCurrentPosition(self):
		if self.iSeek is None:
			return None
		r = self.iSeek.getPlayPosition()
		if r[0]:
			return None
		return int(r[1])

	def getSystemDelay(self, sAudio):
		bInitialized = False
		if self.iService is None:
			self.initAudio()
			bInitialized = True
		iDelay = 0
		if self.iAudioDelay is not None:
			if sAudio == AC3:
				iDelay = self.iAudioDelay.getAC3Delay()
			elif sAudio == PCM:
				iDelay = self.iAudioDelay.getPCMDelay()
			elif sAudio == AC3GLOB:
				iDelay = config.av.generalAC3delay.getValue()
			else:
				iDelay = config.av.generalPCMdelay.getValue()
		if bInitialized == True:
			self.deleteAudio()
		if iDelay == -1:
			iDelay = 0
		return iDelay

	def setSystemDelay(self, sAudio, iDelay, bDelayStart):
		bInitialized = False
		if self.iService is None:
			self.initAudio()
			bInitialized = True
		if self.iAudioDelay is not None:
			iDelayLameDb = iDelay
			if iDelayLameDb == 0:
				iDelayLameDb = -1
			if sAudio == AC3:
				self.iAudioDelay.setAC3Delay(iDelayLameDb)
			elif sAudio == PCM:
				self.iAudioDelay.setPCMDelay(iDelayLameDb)
			elif sAudio == AC3GLOB:
				config.av.generalAC3delay.setValue(iDelay)
				config.av.generalAC3delay.save()
				#Setting the global delay does not activate it, so now we call setAC3Delay to activate the new delay..
				self.iAudioDelay.setAC3Delay(self.systemDelay[AC3])
			else:
				config.av.generalPCMdelay.setValue(iDelay)
				config.av.generalPCMdelay.save()
				#Setting the global delay does not activate it, so now we call setPCMDelay to activate the new delay..
				self.iAudioDelay.setPCMDelay(self.systemDelay[PCM])
		if bInitialized == True:
			self.deleteAudio()
		if bDelayStart == True:
			self.delayedActivateDelay()
		else:
			self.activateDelay()

	def getAudioInformation(self):
		bInitialized = False
		if self.iService is None:
			self.initAudio()
			bInitialized = True

		# check if we are in a recording
		lCurPosition = self.cueGetCurrentPosition()
		if lCurPosition is not None:
			self.bIsRecording = True

		# check if downmix is enabled
		try:
			bDownmixEnabled = config.av.downmix_ac3.value
		except:
			bDownmixEnabled = False

		oAudioTracks = self.iService and self.iService.audioTracks()
		n = oAudioTracks and oAudioTracks.getNumberOfTracks() or 0
		tlist = []
		self.selectedAudioIndex = self.selectedAudioInfo = None
		if n:
			self.selectedAudioIndex = oAudioTracks.getCurrentTrack()
			for x in range(n):
				i = oAudioTracks.getTrackInfo(x)
				languages = i.getLanguage().split('/')
				description = i.getDescription() or ""
				language = ""

				cnt = 0
				for lang in languages:
					if cnt:
						language += ' / '
					if lang in LanguageCodes:
						language += _(LanguageCodes[lang][0])
					elif lang == "und":
						""
					else:
						language += lang
					cnt += 1

				if description and language:
					description += " (" + language + ")"
				else:
					description += language # one of them is not available

				tlist.append((description, x))
				if x == self.selectedAudioIndex:
					if ((description.find("AC3") != -1 or description.find("AC-3") != -1 or description.find("AC3+") != -1) and not bDownmixEnabled) or description.find("DTS") != -1 or description.find("DTS-HD") != -1:
						self.whichAudio = AC3
						self.channelAudio = AC3
					else:
						self.whichAudio = PCM
						self.channelAudio = PCM
					self.selectedAudioInfo = (description, x)
			tlist.sort(key=lambda x: x[0])

		self.audioTrackList = tlist
		for sAudio in AC3PCM:
			self.systemDelay[sAudio] = self.getSystemDelay(sAudio)
		del oAudioTracks
		if bInitialized == True:
			self.deleteAudio()
