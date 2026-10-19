from . import _
from Components.config import config
from enigma import eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from Screens.MessageBox import MessageBox
from timer import TimerEntry
from .PartnerboxFunctions import FillE1TimerList, FillE2TimerList, sendPartnerBoxWebCommand
from .plugin import E2TimerMenu, RemoteTimer, RemoteTimerEntry
import skin

class AllPartnerboxTimerMenu(E2TimerMenu):
	def __init__(self):
		E2TimerMenu.__init__(self, 0)

	def buildEntry(self, timer):
		if int(timer.partnerboxentry.enigma.value):
			entry = E2TimerMenu.buildEntryE1(self, timer)
			timeParam = "PartnerBoxE1TimerTime"
			stateParam = "PartnerBoxE1TimerState"
		else:
			entry = E2TimerMenu.buildEntry(self, timer)
			timeParam = "PartnerBoxE2TimerTime"
			stateParam = "PartnerBoxE2TimerState"

		_, y, _, h = skin.parameters.get(timeParam, (0, 50, 150, 20))
		stateX = skin.parameters.get(stateParam, (150, 50, 150, 20))[0]
		width = self.l.getItemSize().width()
		x = width // 2
		w = width - stateX - x - 10
		if w > 0:
			color = 0x00b0d0d0
			entry.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, timer.partnerboxentry.name.value, color, color))
		return entry


class PartnerboxAllTimers(RemoteTimer):

	def __init__(self, session):
		self.boxes = list(config.plugins.Partnerbox.Entries)
		RemoteTimer.__init__(self, session, self.boxes[0], not_epg=True)
		self.skinName = "RemoteTimer"
		self["timerlist"] = AllPartnerboxTimerMenu()
		self["timerlist"].onSelectionChanged.append(self.selectionChanged)
		self.onClose.append(self._onClose)
		self.setTitle(_("RemoteTimers") + " - " + _("Partnerboxes"))
		self.toggleButtonState()
		self.requestId = 0
		self.pendingTimer = None
		self.closed = False

	def _onClose(self):
		self.closed = True
		self.requestId += 1

	def _setBox(self, timer):
		box = timer.partnerboxentry
		self.PartnerboxEntry = box
		self.password = box.password.value
		self.ip = "%d.%d.%d.%d" % tuple(box.ip.value)
		self.port = box.port.value
		self.http = "http://%s:%d" % (self.ip, self.port)
		self.enigma_type = int(box.enigma.value)
		self.useinternal = int(box.useinternal.value)

	def selectionChanged(self, timer):
		if timer is not None:
			self._setBox(timer)
			self["description"].setText(timer.description)
		else:
			self["description"].setText("")

	def action(self):
		# Fetch independently from every box.  In particular, do not reuse
		# the global remote_timer_list used by the Single EPG integration.
		self.activeBoxes = self.boxes
		if config.plugins.Partnerbox.avahicompare.value:
			from enigma import getPeerStreamingBoxes
			avahiNames = {name.split("//")[1].split(".")[0] for name in getPeerStreamingBoxes() if "//" in name}
			self.activeBoxes = [box for box in self.boxes if box.name.value in avahiNames]

		self.requestId += 1
		requestId = self.requestId
		self.pending = len(self.activeBoxes)
		self.received = []
		self.failed = []
		self["timerlist"].setList([])
		self["timerlist"].instance.hide()
		self["text"].setText(_("Getting Partnerboxes Information..."))
		self.toggleButtonState()
		if not self.pending:
			self["text"].setText(_("No active Partnerboxes found."))
			return
		for box in self.activeBoxes:
			try:
				ip = "%d.%d.%d.%d" % tuple(box.ip.value)
				url = "http://%s:%d%s" % (ip, box.port.value, "/web/timerlist" if int(box.enigma.value) == 0 else "/xml/timers")
				sendPartnerBoxWebCommand(url, None, 10, "root", box.password.value).addCallback(
					self._loaded, box, requestId).addErrback(self._failed, box, requestId)
			except Exception as error:
				self.failed.append(box.name.value)
				print("[PartnerboxAllTimers] %s: %s" % (box.name.value, error))
				self._finished(requestId)

	def _loaded(self, xml, box, requestId):
		if self.closed or requestId != self.requestId:
			return
		try:
			timers = FillE2TimerList(xml) if int(box.enigma.value) == 0 else FillE1TimerList(xml)
			for timer in timers:
				timer.partnerboxentry = box
			self.received.extend(timers)
		except Exception as error:
			self.failed.append(box.name.value)
			print("[PartnerboxAllTimers] %s: %s" % (box.name.value, error))
		self._finished(requestId)

	def _failed(self, error, box, requestId):
		if self.closed or requestId != self.requestId:
			return
		self.failed.append(box.name.value)
		print("[PartnerboxAllTimers] %s: %s" % (box.name.value, error.getErrorMessage()))
		self._finished(requestId)

	def _finished(self, requestId):
		self.pending -= 1
		if self.pending:
			return

		def sortKey(timer):
			if timer.disabled:
				return (2, -timer.timebegin)
			if timer.state >= TimerEntry.StateEnded:
				return (1, -timer.timebegin)
			return (0, timer.timebegin)

		self.E2TimerList = sorted(self.received, key=sortKey)
		self["timerlist"].setList([(timer,) for timer in self.E2TimerList])
		if self.E2TimerList:
			self["timerlist"].instance.show()
		else:
			self["text"].setText(_("No timers found."))
		if self.failed:
			print("[PartnerboxAllTimers] Unavailable: %s" % ", ".join(self.failed))
		timerCount = len(self.E2TimerList)
		boxCount = len(self.activeBoxes) - self.pending - len(self.failed)
		self.setTitle(_("Remote timers: %d, Partnerboxes: %d") % (timerCount, boxCount))
		self.toggleButtonState()

	def getLocations(self):
		self.pendingTimer = self["timerlist"].currentSelection
		if self.pendingTimer is not None:
			self._setBox(self.pendingTimer)
			RemoteTimer.getLocations(self)

	def addTimer(self):
		timer = self.pendingTimer
		if timer is None:
			return
		self._setBox(timer)
		if timer.repeated:
			self.session.open(MessageBox, _("Repeated Timer are not supported!"), MessageBox.TYPE_INFO)
			return
		self.oldstart = timer.timebegin
		self.oldend = timer.timeend
		self.oldtype = timer.type
		self.session.openWithCallback(self.RemoteTimerEntryFinished, RemoteTimerEntry, timer, self.Locations, boxName=self.PartnerboxEntry.name.value)

	def RemoteTimerEntryFinished(self, answer):
		if self.pendingTimer is not None:
			self._setBox(self.pendingTimer)
		if answer:
			RemoteTimer.RemoteTimerEntryFinished(self, answer)

	def deleteTimer(self):
		self.pendingTimer = self["timerlist"].currentSelection
		if self.pendingTimer is not None:
			self._setBox(self.pendingTimer)
			RemoteTimer.deleteTimer(self)

	def deleteTimerConfirmed(self, answer):
		if not answer or self.pendingTimer is None:
			return
		self._setBox(self.pendingTimer)
		# The parent reads the current list selection.  The modal confirmation
		# keeps the selection unchanged, as in the original RemoteTimer.
		RemoteTimer.deleteTimerConfirmed(self, answer)

	def toggleTimer(self):
		timer = self["timerlist"].currentSelection
		if timer is not None:
			self._setBox(timer)
			RemoteTimer.toggleTimer(self)

	def cleanupTimer(self):
		# The blue button applies the original cleanup command to all boxes.
		if not self.activeBoxes:
			return
		self["timerlist"].instance.hide()
		self["text"].setText(_("Cleaning up finished timer entries..."))
		self.cleanupPending = len(self.activeBoxes)
		for box in self.activeBoxes:
			ip = "%d.%d.%d.%d" % tuple(box.ip.value)
			path = "/web/timercleanup?cleanup=true" if int(box.enigma.value) == 0 else "/cleanupTimerList"
			url = "http://%s:%d%s" % (ip, box.port.value, path)
			sendPartnerBoxWebCommand(url, None, 10, "root", box.password.value).addBoth(self._cleaned)

	def _cleaned(self, answer):
		if self.closed:
			return
		self.cleanupPending -= 1
		if not self.cleanupPending:
			self.action()

	def deleteTimerError(self, error=None):
		if error is not None:
			self.session.open(MessageBox, str(error.getErrorMessage()), MessageBox.TYPE_INFO)
			self.action()

	def downloadError(self, error=None):
		self.deleteTimerError(error)
