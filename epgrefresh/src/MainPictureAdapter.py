import Screens.Standby

# MessageBox
from Screens.MessageBox import MessageBox
from Tools import Notifications

import Components.ServiceEventTracker

# Config
from Components.config import config

# eServiceReference
from enigma import eServiceReference, eDVBSatelliteEquipmentControl, eTimer

from . import _, NOTIFICATIONID


class MainPictureAdapter:
	backgroundCapable = True

	def __init__(self, session):
		self.navcore = session.nav
		self.lastCount = None
		self.rotorTimer = eTimer()
		self.rotorTimer.callback.append(self.waitRotorMoving)

	def prepare(self):
		if config.plugins.epgrefresh.enablemessage.value and Screens.Standby.inStandby is None:
			try:
				Notifications.AddPopup(_("EPG refresh starts scanning channels."), MessageBox.TYPE_INFO, 4, NOTIFICATIONID)
			except:
				pass
		self.previousService = self.navcore.getCurrentlyPlayingServiceOrGroup()
		if self.previousService is None and Screens.Standby.inStandby:
			self.previousService = eServiceReference(config.tv.lastservice.value)
		try:
			self.lastCount = Components.ServiceEventTracker.InfoBarCount
		except:
			self.lastCount = None
		return True

	def play(self, service):
		print("[EPGRefresh.MainPictureAdapter.play]")
		try:
			Components.ServiceEventTracker.InfoBarCount = 0
			print("[EPGRefresh.InfoBarCount = 0]")
		except:
			print("[EPGRefresh import error InfoBarCount]")
		return self.navcore.playService(service, checkParentalControl=False, adjust=False)

	def stop(self):
		if Screens.Standby.inStandby:
			if self.previousService is not None:
				self.navcore.playService(self.previousService, forceRestart=True)
				config.tv.lastservice.value = self.previousService.toString()
				config.tv.lastservice.save()
			if not self.rotorTimer.isActive():
				self.rotorTimer.start(1500, True)
		else:
			if self.previousService is not None:
				self.navcore.playService(self.previousService)
				config.tv.lastservice.value = self.previousService.toString()
				config.tv.lastservice.save()
			else:
				self.navcore.stopService()
		try:
			if self.lastCount is not None:
				if Components.ServiceEventTracker.InfoBarCount == 0 and self.lastCount == 1:
					print("[EPGRefresh.InfoBarCount = 1]")
					Components.ServiceEventTracker.InfoBarCount = 1
		except:
			pass

	def waitRotorMoving(self):
		moving = eDVBSatelliteEquipmentControl.getInstance().isRotorMoving()
		if moving:
			if not self.rotorTimer.isActive():
				self.rotorTimer.start(1500, True)
		else:
			self.rotorTimer.stop()
			self.navcore.stopService()
