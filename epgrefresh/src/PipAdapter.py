from __future__ import print_function

from Screens.PictureInPicture import PictureInPicture
from Components.SystemInfo import SystemInfo
from enigma import ePoint, eSize
from Screens.InfoBar import InfoBar

# MessageBox
from Screens.MessageBox import MessageBox
from Tools import Notifications
from Screens import Standby

# Config
from Components.config import config

from . import _, NOTIFICATIONID
PIPNOTIFICATIONID = 'EpgRefreshPipsnowNotificationId'

class PipAdapter:
	backgroundCapable = False
	def __init__(self, session, hide=True):
		if SystemInfo.get("NumVideoDecoders", 1) < 2:
			self.pipAvail = False
			return

		self.hide = hide
		self.session = session
		self.pipAvail = True

	def prepare(self):
		if not self.pipAvail:
			return False

		if config.plugins.epgrefresh.enablemessage.value and Standby.inStandby is None:
			try:
				Notifications.AddPopup(_("EPG refresh started in background.") + "\n" + _("Please don't use PiP meanwhile!"), MessageBox.TYPE_INFO, 4, NOTIFICATIONID)
			except:
				pass
		if hasattr(self.session, 'pipshown') and self.session.pipshown:
			try:
				self.wasShown = True
				self.previousService = self.session.pip.getCurrentService()
				self.previousPath = self.session.pip.servicePath
				self.session.pipshown = False
				if InfoBar.instance:
					if InfoBar.instance.servicelist and InfoBar.instance.servicelist.dopipzap:
						InfoBar.instance.servicelist.togglePipzap()
				if hasattr(self.session, 'pip'):
					del self.session.pip
			except:
				self.wasShown = False
		else:
			self.wasShown = False
		self.initPiP()
		return True

	def hidePiP(self):
		# set pip size to 1 pixel
		print("[EPGRefresh.PipAdapter.hidePiP]")
		x = y = 5
		w = h = 5
		self.session.pip.instance.move(ePoint(x, y))
		self.session.pip.instance.resize(eSize(w, h))
		self.session.pip["video"].instance.resize(eSize(w, h))
		self.session.pip.pipservice = False

	def initPiP(self, new_service=None):
		# Instantiate PiP
		self.session.pip = self.session.instantiateDialog(PictureInPicture)
		self.session.pip.show()
		if new_service is not None:
			newservice = new_service
		else:
			newservice = self.session.nav.getCurrentlyPlayingServiceReference()
		if self.session.pip.playService(newservice):
			self.session.pipshown = True
			self.session.pip.servicePath = InfoBar.instance and InfoBar.instance.servicelist and InfoBar.instance.servicelist.getCurrentServicePath()
			if self.hide: 
				self.hidePiP()
		else:
			self.session.pipshown = False
			try: del self.session.pip
			except Exception: pass

	def play(self, service):
		print("[EPGRefresh.PipAdapter.play]")
		if not self.pipAvail: return False

		if not self.session.pipshown: # make sure pip still exists
			self.initPiP(new_service=service)
			if self.session.pipshown:
				return True
			return False
		else:
			if self.session.pip.playService(service):
				if self.hide: 
					self.hidePiP()
				self.session.pip.servicePath = InfoBar.instance and InfoBar.instance.servicelist and InfoBar.instance.servicelist.getCurrentServicePath()
				return True
			return False

	def stop(self):
		if not self.pipAvail: return
		if config.plugins.epgrefresh.enablemessage.value and Standby.inStandby is None:
			try:
				Notifications.AddPopup(_("EPG refresh finished.") + "\n" + _("PiP available now."), MessageBox.TYPE_INFO, 4, PIPNOTIFICATIONID)
			except:
				pass
		# remove pip preemptively
		try: del self.session.pip
		except Exception: pass

		# reset pip and remove it if unable to play service
		if self.wasShown:
			self.session.pip = self.session.instantiateDialog(PictureInPicture)
			self.session.pip.show()
			if self.session.pip.playService(self.previousService):
				self.session.pip.servicePath = self.previousPath
				self.session.pipshown = True
			else:
				self.session.pipshown = False
				try: del self.session.pip
				except Exception: pass
		else:
			self.session.pipshown = False

