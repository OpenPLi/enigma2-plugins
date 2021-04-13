from __future__ import print_function

from Components.NimManager import nimmanager

# MessageBox
from Screens.MessageBox import MessageBox
from Tools import Notifications
import Screens.Standby
# Config
from Components.config import config

from . import _, NOTIFICATIONID


class RecordAdapter:
	backgroundCapable = True

	def __init__(self, session):
		if len(nimmanager.nim_slots) < 2:
			self.backgroundRefreshAvailable = False
			return

		self.backgroundRefreshAvailable = True
		self.__service = None
		self.navcore = session.nav

	def prepare(self):
		if not self.backgroundRefreshAvailable:
			return False
		if config.plugins.epgrefresh.enablemessage.value and Screens.Standby.inStandby is None:
			try:
				Notifications.AddPopup(_("EPG refresh started in background."), MessageBox.TYPE_INFO, 4, NOTIFICATIONID)
			except:
				pass
		return True

	def play(self, service):
		print("[EPGRefresh.RecordAdapter.play]")
		if not self.backgroundRefreshAvailable:
			return False
		self.stopStreaming()
		self.__service = self.navcore.recordService(service)
		if self.__service is not None:
			self.__service.prepareStreaming()
			self.__service.start()
			return True
		return False

	def stopStreaming(self):
		if self.__service is not None:
			self.navcore.stopRecordService(self.__service)
			self.__service = None

	def stop(self):
		print("[EPGRefresh.RecordAdapter.stop]")
		self.stopStreaming()
